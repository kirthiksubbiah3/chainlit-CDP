import asyncio
from langgraph.graph import StateGraph, START, END
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage
from contextlib import asynccontextmanager, AsyncExitStack
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field
from mcp_agent import mcp_call
from utils import get_logger
from config import app_config

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class State(TypedDict):

    messages: Annotated[list, add_messages]
    alert_details: str
    is_alert: bool
    is_eval: bool


class Alertdetails(BaseModel):
    alert_details: str = Field(description="Get the alert details from the AI message")
    is_alert: bool = Field(
        description="From the AI message, determine if there is an alert or not"
    )
    is_eval: bool = Field(
        description="Indicates whether the current message is being evaluated"
    )


class Observability:
    def __init__(self):
        self.tools = None
        self.llm = None
        self.llm_with_tools = None
        self.graph = None
        self.memory = MemorySaver()
        self.health_llm_call_with_output = None
        self.stream_tokens = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
        }
        self.logger = get_logger(__name__)

        self.servers_to_use = ["slack", "eks"]
        filtered_config = {
            key: mcp_servers_config_to_pass[key]
            for key in self.servers_to_use
            if key in mcp_servers_config_to_pass
        }
        self.mcp_client = MultiServerMCPClient(filtered_config)

    def safe_tools_condition(self, state: State) -> str:
        result = tools_condition(state)

        # Case 1: Already evaluated, no tool to run → END
        if state.get("is_eval", False) and result != "tools":
            self.logger.info("Evaluation complete and no tool needed. Ending.")
            return END

        # Case 2: __end__ before evaluation → send to evaluator
        if result == "__end__" and not state.get("is_eval", False):
            self.logger.info("Tool loop ended, moving to evaluator.")
            return "evaluator"

        # Case 3: __end__ after routing, nothing to do → END
        if result == "__end__" and state.get("is_eval", False):
            self.logger.info("Post-routing __end__, no tools, ending.")
            return END

        # Case 4: Normal tool or evaluator paths
        return result if result in ("tools", "evaluator") else "evaluator"

    def router(self, state: State) -> State:
        # You can optionally log or update messages here
        return {
            "messages": [
                HumanMessage(
                    content=(
                        (
                            "Analyze the alert description and identify the appropriate "
                            "Kubernetes MCP server tools."
                            " Use the cluster name sftp-eks to extract and run the relevant "
                            "kubectl commands."
                            " Based on the output and logs, recommend resolutions for all "
                            "affected Kubernetes resources."
                        )
                    )
                )
            ],
            "alert_details": state["alert_details"],
            "is_alert": state["is_alert"],
            "is_eval": state["is_eval"],
        }

    def agent(self, state: State) -> State:
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def evaluator(self, state: State) -> State:
        last_message = state["messages"][-1]
        self.logger.info("Calling the evaluator")
        last_content = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        system_message = SystemMessage(
            content=(
                "You are an evaluator that finds the alert details from the previous "
                "messages and determines if there is any alert in the output"
            )
        )

        human_message = HumanMessage(
            content=f"""Please extract the following:
    - alert_details: What is the alert and which things needs to be checked with the alert
    - is_alert: Is there an alert or not.

    Here is the message:
    \"\"\"{last_content}\"\"\""""
        )

        evaluator_messages = [system_message, human_message]

        eval_result = self.health_llm_call_with_output.invoke(evaluator_messages)

        new_state = {
            "messages": [
                {"role": "assistant", "content": f"Evaluator findings: {eval_result}"}
            ],
            "alert_details": eval_result.alert_details,
            "is_alert": eval_result.is_alert,
            "is_eval": True,
        }
        return new_state

    async def custom_graph_agent(self, messages, llm, threadid):
        async with self.make_graph() as tools:
            self.llm = llm
            self.llm_with_tools = llm.bind_tools(tools)
            self.health_llm_call_with_output = self.llm.with_structured_output(
                Alertdetails
            )
            graph_builder = StateGraph(State)
            graph_builder.add_node("agent", self.agent)
            graph_builder.add_node("tools", ToolNode(tools=tools))
            graph_builder.add_node("evaluator", self.evaluator)
            graph_builder.add_node("router", self.router)
            # START → agent
            graph_builder.add_edge(START, "agent")

            # From agent, decide: tool call or no tool call
            # If tool is needed → tools; else → evaluator
            graph_builder.add_conditional_edges(
                "agent",
                self.safe_tools_condition,
                {"tools": "tools", "evaluator": "evaluator", END: END},
            )
            # After tools, go back to agent
            graph_builder.add_edge("tools", "agent")

            # Evaluator → router
            graph_builder.add_edge("evaluator", "router")

            # router → agent
            graph_builder.add_edge("router", "agent")
            graph = graph_builder.compile(checkpointer=self.memory)
            usage_totals = await mcp_call(graph, messages, threadid)
            return usage_totals

    @asynccontextmanager
    async def make_graph(self):
        server_names = list(self.mcp_client.connections.keys())
        async with AsyncExitStack() as stack:
            sessions = [
                await stack.enter_async_context(self.mcp_client.session(name))
                for name in server_names
            ]
            tools_per_server = await asyncio.gather(
                *[load_mcp_tools(session) for session in sessions]
            )
            tools = sum(tools_per_server, [])
            yield tools

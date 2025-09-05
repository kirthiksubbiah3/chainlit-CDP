from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition, ToolNode
from pydantic import BaseModel, Field

from config import app_config
from agents.base_agent import BaseAgent
from rag.rag_search import rag_search

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
cluster_name = app_config.cluster_name


class State(TypedDict):

    messages: Annotated[list, add_messages]
    alert_details: str
    is_alert: bool
    is_eval: bool
    question_for_rag: str


class Alertdetails(BaseModel):
    alert_details: str = Field(description="Get the alert details from the AI message")
    is_alert: bool = Field(
        description="From the AI message, determine if there is an alert or not"
    )
    is_eval: bool = Field(
        description="Indicates whether the current message is being evaluated"
    )


class Observability(BaseAgent):
    def __init__(self):
        super().__init__(servers_to_use=["slack", "eks", "grafana"])
        self.state_schema = State
        self.model = Alertdetails
        self.tools = [rag_search]
        self.channel = (
            mcp_servers_config_to_pass.get("slack", {})
            .get("env", {})
            .get("SLACK_CHANNEL_IDS", "")
        )

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
        self.logger.info("Calling the router")
        # You can optionally log or update messages here
        return {
            "messages": [
                HumanMessage(
                    content=(
                        (
                            "Analyze the alert description."
                            "Use the following question to search in the internal document via the "
                            "RAG tool: "
                            f"\"{state.get('question_for_rag', '')}\""
                            "Check in the alert_details document for possible "
                            "solutions."
                            f"Use the cluster name '{cluster_name}' to extract and run the relevant"
                            "kubectl commands."
                            "If no direct solution is found, analyze and recommend actions."
                            "Based on logs and output, recommend resolutions for all affected "
                            "Kubernetes resources if possible"
                            "If the number of resources are high give a generic recommendation "
                            "for all the resources"
                            "If the affected resources are less try to fix the issue after getting"
                            "approval from the user"
                            "Validate after fixing the issue"
                            "If a namespace is stuck in the Terminating state due to finalizers"
                            "patch the namespace by setting its metadata.finalizers to null"
                            "Don't keep on trying the same thing again and again"
                            "Validate using kubernetes alert, don't validate with alert"
                        )
                    )
                )
            ],
            "alert_details": state["alert_details"],
            "is_alert": state["is_alert"],
            "is_eval": state["is_eval"],
            "question_for_rag": state["question_for_rag"],
        }

    def agent(self, state: State) -> State:
        self.logger.info("Calling the agent")
        additional_instruction = HumanMessage(
            content=(
                "You may use Slack or Grafana to get alert details depending on the input.\n"
                f"- If Slack is available, connect to Slack channel {self.channel} "
                "to retrieve alert details.\n"
                "- Otherwise, query Grafana's MCP server (default-group folder) "
                "to get firing alerts.\n"
                "Check for affected resources in the previous messages.\n"
                "Don't keep on trying the same thing again and again."
            )
        )
        messages = state["messages"] + [additional_instruction]
        return {"messages": [self.llm_with_tools.invoke(messages)]}

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

        eval_result = self.llm_structured_output.invoke(evaluator_messages)

        question_for_rag = (
            f"Which instruction should be used for the alert: "
            f"{eval_result.alert_details}?"
        )

        new_state = {
            "messages": [
                {"role": "assistant", "content": f"Evaluator findings: {eval_result}"}
            ],
            "alert_details": eval_result.alert_details,
            "is_alert": eval_result.is_alert,
            "is_eval": True,
            "question_for_rag": question_for_rag,
        }
        return new_state

    def add_nodes_to_graph(self, graph_builder, state: State):

        graph_builder.add_node("tools", ToolNode(tools=self.tool_list))
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

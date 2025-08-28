from typing import Annotated
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition

from config import app_config
from invoke_agent import invoke_agent
from mcp_tools import MCPServerSessionMulti
from tools import get_time_range
from utils import get_logger

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class State(TypedDict):
    messages: Annotated[list, add_messages]


class CryptoWallet:
    def __init__(self):
        self.tools = None
        self.llm = None
        self.llm_with_tools = None
        self.graph = None
        self.memory = MemorySaver()
        self.stream_tokens = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
        }
        self.logger = get_logger(__name__)

        servers_to_use = ["grafana"]
        self.mcp_client = MCPServerSessionMulti(servers_to_use)

    def agent(self, state: State) -> State:
        additional_instruction = SystemMessage(
            content=(
                "You are an agent that queries Grafana dashboards using the Grafana MCP server. "
                "The dashboard to query is always 'Cryptowallet-Log-Dashboard-Level-0'. "
                "From the user's query, identify the panel name they are referring to. "
                "Use the `get_time_range` tool to generate the correct Grafana-compatible time"
                " range "
                "based on user input like 'today', 'yesterday', or 'any time range'. "
                "If the panel returns grouped data (e.g., per currency), format the response "
                "clearly "
                "identify the panel names below which have grouped data: "
                "'No. of transactions per currency type', 'No. of deposits per currency type', "
                "'No. of withdrawals per currency type', 'No. of outgoing transfers per currency "
                "type'. "
                "Return only the relevant data requested by the user from the correct panel."
            )
        )

        messages = state["messages"] + [additional_instruction]
        return {"messages": [self.llm_with_tools.invoke(messages)]}

    async def custom_graph_agent(self, messages, llm, threadid):
        async with self.mcp_client.yield_tools() as tools:
            tools.append(get_time_range)

            self.llm = llm
            self.llm_with_tools = llm.bind_tools(tools)
            graph_builder = StateGraph(State)
            graph_builder.add_node("agent", self.agent)
            graph_builder.add_node("tools", ToolNode(tools=tools))
            graph_builder.add_conditional_edges("agent", tools_condition, "tools")
            graph_builder.add_edge("tools", "agent")
            graph_builder.add_edge(START, "agent")

            graph = graph_builder.compile(checkpointer=self.memory)
            self.logger.info("Compiled Grafana graph successfully")
            usage_totals = await invoke_agent(graph, messages, threadid)
            return usage_totals

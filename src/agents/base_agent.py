import asyncio
from contextlib import asynccontextmanager, AsyncExitStack

from langchain_core.messages import AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from typing_extensions import Annotated, TypedDict

from config import app_config
from invoke_agent import invoke_agent
from utils import get_logger

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class BaseState(TypedDict):
    messages: Annotated[list, add_messages]


class BaseAgent:
    def __init__(self, servers_to_use=None):
        self.logger = get_logger(__name__)
        self.tools = []
        self.llm = None
        self.llm_with_tools = None
        self.memory = MemorySaver()
        self.llm_structured_output = None
        self.stream_tokens = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
        }
        self.tool_list = None
        self.servers_to_use = servers_to_use or []

        mcp_config = {
            key: mcp_servers_config_to_pass[key]
            for key in servers_to_use
            if key in mcp_servers_config_to_pass
        }
        self.mcp_client = MultiServerMCPClient(mcp_config)

        # Define placeholders for state_schema and model, to be set by child
        self.state_schema = None
        self.model = None
        self.agent_node_name = "agent"

    def _get_all_message_content(self, state: BaseState) -> str:
        """
        Collects and concatenates the content of all messages in the state.
        Handles both ChatMessage objects and plain dicts.
        """
        return get_all_message_content(state.get("messages", []))

    def _to_assistant_msg(self, content) -> AIMessage:
        return AIMessage(content)

    def agent(self, state: BaseState) -> BaseState:
        """This node is added to get chunk["agent"]["messages"] in the invoke_agent method.
        Inherit in the subclasses and change as required"""
        return state

    def build_graph(self):
        graph_builder = StateGraph(self.state_schema)
        graph_builder.add_node(self.agent_node_name, self.agent)
        # --- CALL hook for child class to add nodes ---
        if hasattr(self, "add_nodes_to_graph"):
            self.add_nodes_to_graph(graph_builder, self.state_schema)
        graph_builder.add_edge(self.agent_node_name, END)
        graph = graph_builder.compile(checkpointer=self.memory)
        return graph

    @asynccontextmanager
    async def yield_graph(self, llm):
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
            tools.extend(self.tools)
            self.tool_list = tools

            self.llm = llm
            self.llm_with_tools = llm.bind_tools(tools)
            self.llm_structured_output = self.llm.with_structured_output(self.model)
            graph = self.build_graph()

            yield graph

    async def custom_graph_agent(
        self,
        messages,
        llm,
        thread_id,
    ):
        async with self.yield_graph(
            llm,
        ) as graph:
            usage_totals = await invoke_agent(
                graph,
                messages,
                thread_id,
            )
            return usage_totals


def get_all_message_content(messages) -> str:
    """
    Collects and concatenates the content of all messages.
    Handles both ChatMessage objects and plain dicts.
    """
    contents = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            continue
        if hasattr(msg, "content"):
            contents.append(msg.content)
        elif isinstance(msg, dict) and "content" in msg:
            contents.append(msg["content"])
        else:
            contents.append(str(msg))
    return "\n\n".join(contents)

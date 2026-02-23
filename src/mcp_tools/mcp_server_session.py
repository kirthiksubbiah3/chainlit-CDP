"""
MCP server session wrapper.

Creates a temporary MCP session, loads tools, constructs a LangGraph agent,
and invokes it for a single request.
"""

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import app_config
from invoke_agent import invoke_agent

memory = MemorySaver()
mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
multi_server_mcp_client = app_config.multi_server_mcp_client


class MCPServerSession:
    """Encapsulates execution of an agent against a single MCP server."""
    def __init__(self, server, messages, llm, thread_id, buffer=False):
        """Initialize session parameters for a single MCP server run."""
        self.server = server
        self.messages = messages
        self.llm = llm
        self.thread_id = thread_id
        self.buffer = buffer

    async def client_session_per_server(self):
        """Run the agent inside an MCP server session and return usage stats."""
        async with multi_server_mcp_client.session(self.server) as session:
            tools = await load_mcp_tools(session)
            agent = create_react_agent(self.llm, tools, checkpointer=memory)
            usage_totals = await invoke_agent(
                agent, self.messages, self.thread_id, buffer=self.buffer
            )
            return usage_totals

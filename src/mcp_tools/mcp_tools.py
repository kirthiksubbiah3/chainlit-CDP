"""
MCP tools helper module.

Provides access to MCP tools loaded from configured MCP servers
and utility helpers for MCP client creation.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import app_config
from utils import get_logger

logger = get_logger(__name__)

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
multi_server_mcp_client = app_config.multi_server_mcp_client
profiles = app_config.profiles


class MCPTools:
    """Helper class for loading and managing MCP tools."""
    def __init__(self):
        self.profiles_agents = None
        self.tools = None

    async def get_tools(self):
        """Load and cache tools from the configured MCP servers."""
        if not self.tools:
            self.tools = await multi_server_mcp_client.get_tools()
        return self.tools

    # not used anywhere yet
    @staticmethod
    def get_single_mcp_client(server):
        """
        Create and return a MultiServerMCPClient for a single MCP server.

        This is a utility helper and does not depend on instance state.
        """
        mcp_config = mcp_servers_config_to_pass[server].copy()
        mcp_config.pop("chainlit_command", None)
        mcp_client = MultiServerMCPClient({server: mcp_config})
        return mcp_client


mcp_tools = MCPTools()

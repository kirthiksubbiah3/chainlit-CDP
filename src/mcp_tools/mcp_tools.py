from langchain_mcp_adapters.client import MultiServerMCPClient

from config import app_config
from utils import get_logger

logger = get_logger(__name__)

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
multi_server_mcp_client = app_config.multi_server_mcp_client
profiles = app_config.profiles


class MCPTools:
    def __init__(self):
        self.profiles_agents = None
        self.tools = None

    async def get_tools(self):
        if not self.tools:
            self.tools = await multi_server_mcp_client.get_tools()
        return self.tools

    # not used anywhere yet
    def get_single_mcp_client(server):
        mcp_config = mcp_servers_config_to_pass[server].copy()
        mcp_config.pop("chainlit_command", None)
        mcp_client = MultiServerMCPClient({server: mcp_config})
        return mcp_client


mcp_tools = MCPTools()

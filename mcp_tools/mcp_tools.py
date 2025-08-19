from langchain_mcp_adapters.client import MultiServerMCPClient

from agents.react_agent import tools_session_agent
from config import app_config
from llm import get_llm
from utils import get_logger

logger = get_logger(__name__)
profiles = app_config.profiles
mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class MCPTools:
    def __init__(self):
        self.profiles_agents = None

    async def get_profiles_agents(self):
        if self.profiles_agents is None:
            self.profiles_agents = {}
            for profile in profiles:
                llm = get_llm(profile)
                self.profiles_agents[profile] = await tools_session_agent(llm)

    # not used anywhere yet
    def get_single_mcp_client(server):
        mcp_config = mcp_servers_config_to_pass[server].copy()
        mcp_config.pop("chainlit_command", None)
        mcp_client = MultiServerMCPClient({server: mcp_config})
        return mcp_client


mcp_tools = MCPTools()

from agents.react_agent import tools_session_agent
from config import app_config
from llm import get_llm
from utils import get_logger

logger = get_logger(__name__)

mcp_tools_agents = None

profiles = app_config.profiles


async def init_mcp_tools_agents():
    global mcp_tools_agents
    if mcp_tools_agents is None:
        logger.info("Initializing MCP tools agents")
        mcp_tools_agents = {}
        for profile in profiles:
            llm = get_llm(profile)
            mcp_tools_agents[profile] = await tools_session_agent(llm)


# Optionally, you can provide a synchronous getter that ensures initialization
def get_mcp_tools_agents():
    if mcp_tools_agents is None:
        raise RuntimeError(
            "mcp_tools_agents not initialized. Call init_mcp_tools_agents() first."
        )
    return mcp_tools_agents

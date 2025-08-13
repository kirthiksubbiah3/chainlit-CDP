from langchain_mcp_adapters.client import MultiServerMCPClient

from config import app_config
from utils import get_logger

logger = get_logger(__name__)


mcp_servers_config = app_config.mcp_servers_config


def get_single_mcp_client(server):
    mcp_config = mcp_servers_config[server].copy()
    mcp_config.pop("chainlit_command", None)
    mcp_client = MultiServerMCPClient({server: mcp_config})
    return mcp_client

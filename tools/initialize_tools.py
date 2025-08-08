import asyncio

from config import app_config
from rag.rag_search import rag_search
from utils import get_logger

logger = get_logger(__name__)

mcp_client = app_config.mcp_client

_cached_tools = {"tools": None}
tools_lock = asyncio.Lock()


async def initialize_tools():
    """Initializes tools once and returns cached version."""
    logger.info("Initializing tools...")
    if _cached_tools["tools"] is None:
        logger.info("Tools not loaded yet, waiting for lock to fetch tools...")
        async with tools_lock:
            if _cached_tools["tools"] is None:
                logger.info("Lock acquired, fetching tools now...")
                try:
                    tools = await mcp_client.get_tools()
                    logger.debug("Fetched tools from mcp client: %s", tools)
                    tools.append(rag_search)
                    logger.debug("Extended tools with rag_search: %s", tools)
                    _cached_tools["tools"] = tools
                    logger.info("Tools fetched and cached successfully.")
                except asyncio.TimeoutError as e:
                    logger.error("Timeout while fetching tools: %s", e)
                    _cached_tools["tools"] = None  # Ensure cache remains unset on error
                except ConnectionError as e:
                    logger.error("Connection error while fetching tools: %s", e)
                    _cached_tools["tools"] = None  # Ensure cache remains unset on error
            else:
                logger.info(
                    "Tools were fetched while waiting for lock, using cached tools."
                )
    else:
        logger.info("Tools already cached, using cached tools.")
    return _cached_tools["tools"]

import asyncio

from utils import get_logger
from vars import mcp_client
from rag.rag_search import rag_search

logger = get_logger(__name__)


_cached_tools = {"tools": None}
tools_lock = asyncio.Lock()


async def initialize_tools():
    """Initializes tools once and returns cached version."""
    if _cached_tools["tools"] is None:
        logger.info("Tools not loaded yet, waiting for lock to fetch tools...")
        async with tools_lock:
            if _cached_tools["tools"] is None:
                logger.info("Lock acquired, fetching tools now...")
                try:
                    tools = await mcp_client.get_tools()
                    tools.append(rag_search)
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

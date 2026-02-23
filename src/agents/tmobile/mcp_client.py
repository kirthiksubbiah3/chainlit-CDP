"""
Atlassian MCP client integration.

Manages MCP sessions, tool loading, and LangGraph agent execution
for Atlassian-related workflows.
"""

import asyncio
import logging
from contextlib import AsyncExitStack

from fastapi import APIRouter

from langgraph.prebuilt import create_react_agent
from langchain_core.runnables.config import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import MemorySaver

# Import tools from src/tools
from tools import (
    get_atlassian_org_users_or_accounts,
    get_atlassian_user_role_assignments,
    get_jsm_project_portals,
    get_jsm_request_types,
    get_jsm_forms,
)

# Import local modules
from utils import get_logger
from .llm import llm_router
from .mcp_manager import mcp

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

multi_server_mcp_client = MultiServerMCPClient(mcp.get_enabled_mcps())

router = APIRouter()


class AtlassianMCPClient:
    """Client responsible for managing Atlassian MCP interactions."""
    def __init__(self):
        self.llm = None
        self.agent = None
        self.tools = []
        self.sessions = []
        self.stack = AsyncExitStack()
        self._tool_map = {}
        self.initialized = False
        self.MAX_ITERATIONS = 3
        self.checkpoint_memory = MemorySaver()

    async def __aenter__(self):
        await self.stack.__aenter__()
        await self.setup()
        self.initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stack.__aexit__(exc_type, exc_val, exc_tb)
        self.initialized = False

    async def setup(self):
        """Initialize MCP sessions, tools, and LangGraph agent."""
        server_names = ["atlassian"]

        if "atlassian" not in mcp.get_enabled_mcps():
            logger.error("❌ 'atlassian' MCP config not found")
            return

        logger.info("🔗 Connecting to Atlassian MCP")

        self.sessions = [
            await self.stack.enter_async_context(
                multi_server_mcp_client.session(server)
            )
            for server in server_names
        ]

        tools_lists = await asyncio.gather(*map(load_mcp_tools, self.sessions))
        all_tools = sum(tools_lists, [])

        # Add additional Atlassian tools
        all_tools += [
            get_atlassian_org_users_or_accounts,
            get_atlassian_user_role_assignments,
            get_jsm_project_portals,
            get_jsm_request_types,
            get_jsm_forms,
        ]

        self.tools = [
            t for t in all_tools if getattr(t, "name", None) != "add_inline_policy"
        ]

        logger.info(f"✅ Loaded {len(self.tools)} tools")
        logger.info(f"🔧 Tools: {[t.name for t in self.tools]}")

        self.llm = llm_router.get_llm()
        self._tool_map = {t.name: t for t in self.tools}
        self.agent = create_react_agent(
            self.llm, tools=self.tools, checkpointer=self.checkpoint_memory
        )

    async def invoke(
        self,
        messages: list,
        thread_id: str,
        user_id: str | None = None,
        request_id: str | None = None,
    ):
        """Invoke the agent and return the final message content."""
        runnable_config: RunnableConfig = {
            "configurable": {"thread_id": thread_id},
            "metadata": {
                "user_id": user_id,
                "request_id": request_id,
            },
        }
        result = await self.agent.ainvoke({"messages": messages}, runnable_config)
        return result["messages"][-1].content

    async def stream(
        self,
        messages: list,
        thread_id: str,
        user_id: str | None = None,
        request_id: str | None = None,
    ):
        """Stream agent execution events."""
        runnable_config: RunnableConfig = {
            "configurable": {"thread_id": thread_id},
            "metadata": {
                "user_id": user_id,
                "request_id": request_id,
            },
        }
        async for event in self.agent.astream(
            {"messages": messages},
            runnable_config,
            stream_mode="updates",
        ):
            yield event


mcp_client: AtlassianMCPClient | None = None
mcp_lock = asyncio.Lock()


async def get_mcp_client():
    """Return a singleton initialized MCP client."""
    global mcp_client
    async with mcp_lock:
        if mcp_client is None or not mcp_client.initialized:
            mcp_client = AtlassianMCPClient()
            await mcp_client.__aenter__()
        return mcp_client

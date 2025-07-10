import asyncio
from contextlib import asynccontextmanager, AsyncExitStack
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from tools_manager import initialize_tools

from vars import mcp_client
from mcp_agent import mcp_call

memory = MemorySaver()


async def tools_session_agent(messages, llm, threadid):
    agent = create_react_agent(llm, await initialize_tools(), checkpointer=memory)
    usage_totals = await mcp_call(agent, messages, threadid)
    return usage_totals


async def server_session_agent(messages, llm, threadid):
    async with make_graph() as tools:
        agent = create_react_agent(llm, tools, checkpointer=memory)
        usage_totals = await mcp_call(agent, messages, threadid)
        return usage_totals


@asynccontextmanager
async def make_graph():
    server_names = list(mcp_client.connections.keys())
    async with AsyncExitStack() as stack:
        sessions = [
            await stack.enter_async_context(mcp_client.session(name))
            for name in server_names
        ]
        tools_per_server = await asyncio.gather(
            *[load_mcp_tools(session) for session in sessions]
        )
        tools = sum(tools_per_server, [])
        yield tools

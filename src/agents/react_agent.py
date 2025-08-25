import asyncio
from contextlib import asynccontextmanager, AsyncExitStack

from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from config import app_config
from tools import generate_docx, generate_pdf
from utils import get_logger
from invoke_agent import invoke_agent

logger = get_logger(__name__)

memory = MemorySaver()

mcp_client = app_config.mcp_client


async def invoke_react_agent(agent, messages, thread_id, buffer=False):
    logger.info("Invoking react agent for thread_id: %s", thread_id)
    usage_totals = await invoke_agent(agent, messages, thread_id, buffer=buffer)
    logger.info("React agent completed for thread_id: %s", thread_id)
    return usage_totals


async def single_mcp_client(server_params, llm, messages, thread_id):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            # Get tools
            tools = await load_mcp_tools(session)
            # Create and run the agent
            agent = create_react_agent(llm, tools, checkpointer=memory)
            return await invoke_react_agent(agent, messages, thread_id)


async def tools_mcp_server_agent(mcp_server, messages, llm, thread_id, buffer=False):
    async with mcp_client.session(mcp_server) as session:
        tools = await load_mcp_tools(session)
        agent = create_react_agent(llm, tools, checkpointer=memory)
        return await invoke_react_agent(agent, messages, thread_id, buffer=buffer)


async def server_session_agent(llm, messages, thread_id, single_mcp_client):
    async with make_graph(single_mcp_client) as tools:
        agent = create_react_agent(llm, tools, checkpointer=memory)
        return await invoke_react_agent(agent, messages, thread_id)


def extend_with_custom_tools(tools):
    logger.info("Extending tools with custom PDF and DOCX generators")
    tools.extend([generate_pdf, generate_docx])


@asynccontextmanager
async def make_graph(single_mcp_client=None):
    client = single_mcp_client or mcp_client

    server_names = list(client.connections.keys())
    logger.info("Creating async graph for servers: %s", server_names)
    async with AsyncExitStack() as stack:
        sessions = [
            await stack.enter_async_context(client.session(name))
            for name in server_names
        ]
        logger.info("Loaded sessions for servers")
        tools_per_server = await asyncio.gather(
            *[load_mcp_tools(session) for session in sessions]
        )
        logger.info("Loaded tools for all servers")
        tools = sum(tools_per_server, [])
        extend_with_custom_tools(tools)
        logger.info("Yielding tools from make_graph")
        yield tools

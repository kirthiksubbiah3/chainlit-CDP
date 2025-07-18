import asyncio
from contextlib import asynccontextmanager, AsyncExitStack
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from tools import generate_docx, generate_pdf, initialize_tools

from utils import get_logger
from vars import mcp_client
from mcp_agent import mcp_call

logger = get_logger(__name__)

memory = MemorySaver()


async def invoke_react_agent(messages, llm, tools, threadid):
    logger.info("Invoking react agent for threadid: %s", threadid)
    agent = create_react_agent(llm, tools, checkpointer=memory)
    usage_totals = await mcp_call(agent, messages, threadid)
    logger.info("React agent completed for threadid: %s", threadid)
    return usage_totals


async def tools_session_agent(messages, llm, threadid):
    logger.info("Initializing tools for tools session agent")
    tools = await initialize_tools()
    extend_with_custom_tools(tools)
    return await invoke_react_agent(messages, llm, tools, threadid)


async def server_session_agent(messages, llm, threadid):
    logger.info("Starting server session agent for threadid: %s", threadid)
    async with make_graph() as tools:
        return await invoke_react_agent(messages, llm, tools, threadid)


def extend_with_custom_tools(tools):
    logger.info("Extending tools with custom PDF and DOCX generators")
    tools.extend([generate_pdf, generate_docx])


@asynccontextmanager
async def make_graph():
    server_names = list(mcp_client.connections.keys())
    logger.info("Creating async graph for servers: %s", server_names)
    async with AsyncExitStack() as stack:
        sessions = [
            await stack.enter_async_context(mcp_client.session(name))
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

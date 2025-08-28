import asyncio
from contextlib import asynccontextmanager, AsyncExitStack

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools


class MCPServerSessionMulti:
    def __init__(self, mcp_config):
        self.mcp_client = MultiServerMCPClient(mcp_config)

    @asynccontextmanager
    async def yield_tools(self):
        server_names = list(self.mcp_client.connections.keys())
        async with AsyncExitStack() as stack:
            sessions = [
                await stack.enter_async_context(self.mcp_client.session(name))
                for name in server_names
            ]
            tools_per_server = await asyncio.gather(
                *[load_mcp_tools(session) for session in sessions]
            )
            tools = sum(tools_per_server, [])

            yield tools

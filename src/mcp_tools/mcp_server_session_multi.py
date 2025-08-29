import asyncio
from contextlib import asynccontextmanager, AsyncExitStack

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from config import app_config

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class MCPServerSessionMulti:
    # mcp_config can contain one or more server configurations
    def __init__(self, server_names):
        mcp_config = {
            key: mcp_servers_config_to_pass[key]
            for key in server_names
            if key in mcp_servers_config_to_pass
        }
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

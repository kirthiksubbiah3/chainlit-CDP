from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from invoke_agent import invoke_agent
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from config import app_config

memory = MemorySaver()
mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass


class MCPServerSession:
    def __init__(self):
        self.server_params = {}

    def get_server_params(self, server):
        if server not in self.server_params:
            self.server_params[server] = StdioServerParameters(
                **mcp_servers_config_to_pass[server]
            )

    async def single_mcp_client(self, server, llm, messages, thread_id):
        self.get_server_params(server)
        server_params = self.server_params[server]
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                # Get tools
                tools = await load_mcp_tools(session)
                # Create and run the agent
                agent = create_react_agent(llm, tools, checkpointer=memory)
                usage_totals = await invoke_agent(agent, messages, thread_id)
                return usage_totals


mcp_server_session = MCPServerSession()

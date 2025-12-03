from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import app_config
from llm import get_llm
from mcp_tools import mcp_tools
from rag.rag_search import rag_search
from rag.sftp_rag_tool import readme_rag_search
from rag.confluence_rag_tool import confluence_rag_search
from tools import generate_docx, generate_pdf, read_attachment, generate_mermaid_diagram
from utils import get_logger

logger = get_logger(__name__)
memory = MemorySaver()
profiles = app_config.profiles


class DefaultAgents:
    def __init__(self):
        self.profiles_agents = None
        self.tools = None

    async def get_tools(self):
        if not self.tools:
            self.tools = await mcp_tools.get_tools()
            self.tools += [generate_docx, generate_pdf, rag_search, read_attachment,
                           generate_mermaid_diagram, readme_rag_search, confluence_rag_search]
            logger.info("Loaded tools: %s", [tool.name for tool in self.tools])

    async def get_profiles_agents(self):
        if self.profiles_agents is None:
            await self.get_tools()
            self.profiles_agents = {}
            for profile in profiles:
                llm = get_llm(profile)
                self.profiles_agents[profile] = create_react_agent(
                    llm, self.tools, checkpointer=memory
                )
        logger.info("Loaded profiles agents: %s", self.profiles_agents.keys())


default_agents = DefaultAgents()


def default_agent(profile):
    agent = default_agents.profiles_agents[profile]
    return agent

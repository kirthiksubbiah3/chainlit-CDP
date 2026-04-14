"""
Default agent orchestration module.

Creates and manages LangGraph ReAct agents for each configured profile
using shared tools, memory, and MCP integrations.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import app_config
from llm import get_llm
from mcp_tools import mcp_tools
from tools import (
    get_atlassian_org_users_or_accounts,
    get_atlassian_user_role_assignments,
    create_jira_project,
    create_confluence_space,
    get_jsm_project_portals,
    get_jsm_request_types,
    get_jsm_forms,
    rag_search,
    get_gitlab_projects,
    get_gitlab_pipelines,
    get_gitlab_jobs,
    get_gitlab_job_logs,
)
from utils import get_logger

logger = get_logger(__name__)
memory = MemorySaver()
profiles = app_config.profiles


class DefaultAgents:
    """Manages default LangGraph agents per configured profile."""
    def __init__(self):
        self.profiles_agents = None
        self.tools = None

    async def get_tools(self):
        """Load and cache all tools required by default agents."""
        if not self.tools:
            self.tools = await mcp_tools.get_tools()
            self.tools += [
                get_atlassian_org_users_or_accounts,
                get_atlassian_user_role_assignments,
                create_jira_project,
                create_confluence_space,
                get_jsm_project_portals,
                get_jsm_request_types,
                get_jsm_forms,
                rag_search,
                get_gitlab_projects,
                get_gitlab_pipelines,
                get_gitlab_jobs,
                get_gitlab_job_logs,
            ]
            logger.info("Loaded tools: %s", [tool.name for tool in self.tools])

    async def get_profiles_agents(self):
        """Initialize and return agents for all configured profiles."""
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
    """Return the default agent for the given profile."""
    agent = default_agents.profiles_agents[profile]
    return agent

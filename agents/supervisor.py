# %%
import os
import warnings
from dotenv import load_dotenv

from langgraph_supervisor import create_supervisor
from agents.browser_automation_agent import browser_agent
from models.bedrock import Bedrock

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Load environment variables
load_dotenv()

# Disable telemetry
os.environ["LANGCHAIN_ENDPOINT"] = "disabled"

# Initialize Claude (no thinking mode for now)
model = Bedrock().get_model_details()

# %%
# pylint: disable=R0903
class Supervisor:
    """LangGraph Supervisor that routes tasks to the appropriate agent."""
    def __init__(self):
        pass

    def workflow(self):
        """
        Builds LangGraph workflow:
        - RAG step
        - Browser/API agents
        - Validation
        """
        workflow = create_supervisor(
            agents=[
                browser_agent,
            ],
            model=model,
            prompt=(
                "You are a smart AI supervisor. "
                # "Start with retrieving similar tasks (RAG). "
                "Route to the right agent: browser, API, or validator. "
                "For anything involving url or health checks, use browser_agent. "
                "Store key messages in memory. Be precise and efficient."
            )
        )

        return workflow

# %%

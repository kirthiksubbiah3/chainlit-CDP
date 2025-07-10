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

# --- Configuration ---
# Load the URL to make the supervisor aware of its domain of operation
LOGIN_URL = os.getenv("ANTHEM_LOGIN_URL")

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
        Builds the LangGraph workflow.
        The supervisor will route to the browser_agent for automation tasks
        or respond directly for general conversation.
        """
        workflow = create_supervisor(
            agents=[
                browser_agent,
            ],
            model=model,
            prompt=(
                "You are a highly specialized AI supervisor for an internal "
                "software automation team. "
                "Your SOLE area of responsibility is managing tasks for the "
                "corporate portal "
                f"located at domain: **{LOGIN_URL}**.\n\n"
                "Your role:\n"
                "1.  **DELEGATE RELEVANT TASKS**: If a user asks for a "
                "'health check', 'validation', 'test', 'login', or any other "
                "task that is clearly related to our corporate portal, you "
                "MUST delegate the **exact original user request** to the "
                "`browser_agent`.\n"
                "2.  **REJECT IRRELEVANT TASKS**: If the user asks about "
                "anything unrelated to this portal (e.g., public websites "
                "like google.com, "
                "checking stock prices, asking about the weather), "
                "you MUST POLITELY REFUSE. "
                "Explain that you are a specialized tool for internal portal "
                "automation and cannot perform general web browsing.\n"
                "3.  **HANDLE CONVERSATION**: For general greetings "
                "('hi', 'hello') or questions about your purpose, respond "
                "directly and helpfully, reminding them of your specialized "
                "function."
            ),
        )

        return workflow


# %%

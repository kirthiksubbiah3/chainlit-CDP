# %%
import os
import asyncio
import warnings

from dotenv import load_dotenv
from browser_use import Agent
from langgraph.prebuilt import create_react_agent
from models.bedrock import Bedrock

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Load .env variables
load_dotenv()

# Read credentials and URL from env
anthem_username = os.getenv("anthem_username")
anthem_password = os.getenv("anthem_password")
login_url = os.getenv("ANTHEM_LOGIN_URL",
                      "https://sydneymember.demoportal.anthem.com/member/public/demo-login")

# Disable telemetry
os.environ["LANGCHAIN_ENDPOINT"] = "disabled"

# Load Claude model with tool support (no thinking!)
model_browser = Bedrock().get_model_details()

# %%
def run_browser_agent(task: str) -> str:
    """
    Use the Claude-powered browser agent to log in and perform task-related checks.
    URL and credentials are loaded from environment.
    """
    async def _inner():
        agent = Agent(
            task=(
                f"Navigate to the following url {login_url} "
                f"and the following credentials to login: "
                f"username {anthem_username}, password {anthem_password} ."
                f"Perform the task: {task}"
            ),
            llm=model_browser,
            use_vision=True,
            max_failures=8,
            # save_conversation_path="logs/conversation",  # Optional
        )
        history = await agent.run()
        return history.extracted_content()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_inner())


# ✅ LangGraph-compatible React Agent
browser_agent = create_react_agent(
    model=model_browser,
    tools=[run_browser_agent],
    name="browser_expert",
    prompt = (
        "You are an expert in browser automation and intelligent web interaction. "
        "Your task is to use the available browser tool to perform actions such as logging in, "
        "navigating pages, submitting forms, and verifying page content. "
        "Always read the user's task carefully and reason step-by-step before deciding what to do. "
        "Prioritize reliability, precision, and clarity when interacting with the webpage. "
        "If the task involves checking for errors, "
        "verify whether error messages are visible after interaction."
    ),
)

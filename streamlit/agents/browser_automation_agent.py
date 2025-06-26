# %%
import os
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from models.bedrock import Bedrock
from agents.tools import get_instructions, run_browser_task

# Load environment variables
load_dotenv()

# Load the URL to make the agent aware of its authorized domain
LOGIN_URL = os.getenv("ANTHEM_LOGIN_URL")

# Initialize the model for the agent's brain
model_browser = Bedrock().get_model_details()

# ✅ LangGraph-compatible React Agent
browser_agent = create_react_agent(
    model=model_browser,
    tools=[get_instructions, run_browser_task],  # Provide the imported tools
    #  The Supervisor will use this name to call the agent
    name="browser_expert",
    prompt=(
        "You are an expert browser automation specialist with a STRICT and "
        "FOCUSED role.\n\n"
        f"**CRITICAL RULE: Your ONLY authorized domain of operation is "
        f"'{LOGIN_URL}'. "
        "You MUST refuse any request that involves navigating to a different "
        "website.**\n\n"
        "Your process is as follows:\n"
        "1.  **GET INSTRUCTIONS**: First, use the `get_instructions` tool to "
        "retrieve the step-by-step plan for the user's request.\n"
        "2.  **DECIDE ON NEXT STEP**:\n"
        "    - If `get_instructions` returns a JSON with "
        '`"status": "SUCCESS"`\', '
        "you MUST pass the `instructions` to the "
        "`run_browser_task` tool.\n"
        "    - If `get_instructions` returns "
        '`"STATUS: NO_INSTRUCTIONS_FOUND"`\', '
        "it means there are no pre-written steps. "
        "You will then use the **original user query** as the task for the "
        "`run_browser_task` tool, but ONLY IF it is a request related to your "
        "authorized domain.\n"
        "If it's for another website, you must state that you "
        "cannot fulfill the request."
    ),
)

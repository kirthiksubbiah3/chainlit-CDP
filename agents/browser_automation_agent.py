import asyncio
import os
import sys

from browser_use import Agent
from langgraph.prebuilt import create_react_agent
from models.bedrock import bedrock
from dotenv import load_dotenv

load_dotenv()
model_details = bedrock("us.anthropic.claude-3-7-sonnet-20250219-v1:0")
model = model_details.get_model_details()

anthem_username = os.getenv("anthem_username")
print(anthem_username)
anthem_password = os.getenv("anthem_password")
print(anthem_password)


def run_browser_agent(task: str) -> str:
    """Use a browser agent to perform the given web automation task (e.g., navigate to a URL and check for errors).
    The url is constant. Everytime navigate to the same url https://sydneymember.demoportal.anthem.com/member/public/demo-login
    Use the following credentials to login. Use the value stored in anthem_username for username and the value stored in anthem_password for password.
    """

    async def _inner():

        agent = Agent(
            task=f"Navigate to the following url https://sydneymember.demoportal.anthem.com/member/public/demo-login and the following credentials to login: username: {anthem_username}, password: {anthem_password}"
            + task,
            llm=model,
            max_failures=8,
            use_vision=True,  # Defaulting to True as per original script
            save_conversation_path="logs/conversation",
        )
        history = await agent.run()
        return history.extracted_content()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_inner())


browser_agent = create_react_agent(
    model=model,
    tools=[run_browser_agent],  # `task` will be auto-inferred
    name="browser_expert",
    prompt="You are a browser automation expert. Use the tool to perform user-defined web tasks like health checks, form filling, or scraping.",
)

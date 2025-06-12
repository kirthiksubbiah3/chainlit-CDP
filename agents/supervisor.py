from langgraph_supervisor import create_supervisor
from agents import browser_automation_agent
from models.bedrock import bedrock
from dotenv import load_dotenv

model_details = bedrock("us.anthropic.claude-3-7-sonnet-20250219-v1:0")
model = model_details.get_model_details()

load_dotenv()


class supervisor:
    def __init__(self):
        pass

    def workflow(self):

        workflow = create_supervisor(
            agents=[browser_automation_agent.browser_agent],
            model=model,
            prompt=(
                "You are a team supervisor managing a browser automation expert. "
                "For anything involving url or health checks, use browser_agent. "
            ),
        )
        return workflow

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

# Load environment variables
load_dotenv()
assert os.getenv("GOOGLE_API_KEY"), "Missing GOOGLE_API_KEY in .env"

# MCP server configuration
SERVER_CONFIGS = {
    "playwright": {
        "command": "npx",
        "args": [
            "-y",
            "mcp-playwright-network@latest",
            "--ignore-https-errors",
            "--isolated",
            "--browser",
            "firefox",
        ],
        "transport": "stdio",
    },
}

client = MultiServerMCPClient(SERVER_CONFIGS)


@asynccontextmanager
async def make_graph():
    async with client.session("playwright") as session:
        tools = await load_mcp_tools(session)
        print("✅ Loaded tools:", [tool.name for tool in tools])
        agent = create_react_agent(
            model="google_genai:gemini-2.5-flash",
            tools=tools,
            max_iterations=50,
        )
        yield agent


APP_URL = "https://ai-dev.sflabs.ustpace.com/login"


async def run_tests_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tests = [line.strip() for line in f if line.strip()]

    results = []
    max_attempts = 3

    async with make_graph() as agent:
        for i, test in enumerate(tests, start=1):
            print(f"\n🚀 Running Test {i}: {test}")
            status = "unknown"
            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                print(f"Attempt {attempt} for Test {i}")
                try:
                    response = await agent.ainvoke(
                        {
                            "messages": [
                                {
                                    "role": "system",
                                    "content": (
                                        f"You are an automation testing agent. "
                                        f"The application URL is {APP_URL}. "
                                        f"For each test case, execute the "
                                        f"steps using the given MCP tools."
                                    ),
                                },
                                {"role": "user", "content": test},
                            ]
                        }
                    )
                    print("🔍 Response:", response)

                    messages = response.get("messages", [])
                    if messages:
                        message = messages[-1]  # Get the final AIMessage
                        if hasattr(message, "content"):
                            content = message.content.strip().lower()
                        else:
                            content = ""

                        # Try to parse as JSON first
                        try:
                            result_data = json.loads(content)
                            status_value = result_data.get("status", "")
                        except json.JSONDecodeError:
                            # Fallback to string matching
                            if "success" in content:
                                status_value = "success"
                            elif "failure" in content:
                                status_value = "failure"
                            else:
                                status_value = ""

                        if status_value == "success":
                            status = "passed"
                        elif status_value == "failure":
                            status = "failed"
                        else:
                            status = "unknown"
                    else:
                        print(
                            "⚠️ No message found in response. Skipping status check."
                        )
                        status = "unknown"
                except Exception as e:
                    print(f"❌ Error during Test {i}: {e}")
                    status = "error"

                if status in ["passed", "failed", "error"]:
                    break
                elif attempt == max_attempts:
                    print(f"⚠️ Max attempts reached for Test {i}.")
            results.append((f"Test {i}", status))

    print("\n📋 Test Summary:")
    for test_name, result in results:
        print(f"{test_name}: {result}")


if __name__ == "__main__":
    # ✅ Use your full file path here
    base_dir = Path(__file__).parent
    test_file_path = base_dir / "tests.txt"

    asyncio.run(run_tests_from_file(test_file_path))

"""
LLM agent made with langchain and chainlit
"""
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import yaml
import chainlit as cl

load_dotenv()

# Available commands in the UI
COMMANDS = [
    {
        "id": "Browser",
        "icon": "globe",
        "description": "Search through browser",
        "button": True,
        "persistent": True
    },
]

with open("./config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

mcp_servers_config = config['mcp']['servers']
llm_bedrock_config = config['llm']['bedrock']

# Initialize the Claude model via Bedrock
# Credentials are in .env
llm = ChatBedrockConverse(**llm_bedrock_config)

async def mcp_call(
        messages: List[BaseMessage],
        server_params: StdioServerParameters
    ) -> List[BaseMessage]:
    """Function to call mcp servers"""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(llm, tools)
            agent_response = await agent.ainvoke({
                "messages": messages
            })

            response = []

            for message in agent_response['messages']:
                response.append(message)
                if not isinstance(message, AIMessage):
                    continue

                if message.tool_calls and isinstance(message.content, list):
                    for chunk in message.content:
                        if isinstance(chunk, dict) and chunk['type'] == 'text':
                            await cl.Message(content=f"🤖 {chunk['text']}").send()
                else:
                    await cl.Message(content=f"🤖 {message.content}").send()

            return response

@cl.oauth_callback
def auth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_app_user: cl.User
) -> Optional[cl.User]:
    """Chainlit hook for oauth call back"""

    if provider_id == "keycloak" and token and raw_user_data:
        return default_app_user
    raise ValueError(
        "401, Authentication failed: Unsupported provider or invalid token.",
    )

@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    await cl.context.emitter.set_commands(COMMANDS)
    await cl.Message(
        content='🤖 Hello, welcome to Sentinel Mind! How can I help you?'
    ).send()

@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    messages = [HumanMessage(content=msg.content)]
    start_time = time.perf_counter()
    # fetch mcp server to be used when msg.command is None by default
    server_params = StdioServerParameters(**mcp_servers_config['fetch'])
    if msg.command == 'Browser':
        server_params = StdioServerParameters(**mcp_servers_config['playwright'])

    await mcp_call(messages, server_params)

    end_time = time.perf_counter()
    time_taken = int(end_time - start_time)
    minutes, seconds = divmod(time_taken, 60)

    content = (
        f"🤖 Time taken for this response: "
        f"{f'{minutes} minute{"s" if minutes != 1 else ""} ' if minutes > 0 else ''}"
        f"{seconds} second{'s' if seconds != 1 else ''}"
    )

    await cl.Message(content=content).send()

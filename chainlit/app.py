"""
LLM agent made with langchain and chainlit
"""

from dotenv import load_dotenv

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import chainlit as cl

load_dotenv()

# Initialize the Claude model via Bedrock
# Credentials are in .env
llm = ChatBedrockConverse(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    temperature=0.0,
)

server_params = StdioServerParameters(
    command="npx",
    args=["@playwright/mcp@latest", "--ignore-https-errors"],
    env={
        "DISPLAY": ":1"
    }
)

async def mcp_call(messages: HumanMessage) -> None:
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
                "messages": [messages]
            })

            for message in agent_response['messages']:
                if not isinstance(message, AIMessage):
                    continue

                if message.tool_calls and isinstance(message.content, list):
                    for chunk in message.content:
                        if isinstance(chunk, dict) and chunk['type'] == 'text':
                            await cl.Message(content=f"🤖 {chunk['text']}").send()
                else:
                    await cl.Message(content=f"🤖 {message.content}").send()

@cl.on_chat_start
async def on_chat_start():
    """On chat start chainlit hook"""
    await cl.Message(
        content='🤖 Hello, welcome to Sentinel Mind! How can I help you?'
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """On message chainlit hook"""    
    await mcp_call(HumanMessage(content=message.content))

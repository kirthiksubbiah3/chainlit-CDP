"""
LLM agent made with langchain and chainlit
"""

from typing import List
from dotenv import load_dotenv

import yaml
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import chainlit as cl

load_dotenv(override=True)

# Load config
with open("./config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

mcp_servers_config = config["mcp"]["servers"]
llm_bedrock_config = config["llm"]["bedrock"]

# Initialize the Claude model via Bedrock
# Credentials are in .env
llm = ChatBedrockConverse(**llm_bedrock_config)


async def mcp_call(
    messages: List[HumanMessage],
    server_params: StdioServerParameters,
) -> None:
    """Function to call mcp servers"""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            msg_processing = cl.Message(content="Processing...")
            await msg_processing.send()

            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(llm, tools)
            async for chunk in agent.astream(
                {"messages": messages},
                {"recursion_limit": 100},
                stream_mode="updates",
            ):
                await msg_processing.send()
                if "agent" not in chunk:
                    continue

                for message in chunk["agent"]["messages"]:
                    if not isinstance(message, AIMessage):
                        continue

                    msg = cl.Message(content="")
                    if (
                        message.tool_calls and
                        isinstance(message.content, list)
                    ):
                        for chunk in message.content:
                            if (
                                isinstance(chunk, dict) and
                                chunk["type"] == "text"
                            ):
                                await msg.stream_token(f"🤖 {chunk['text']}")
                    else:
                        await msg.stream_token(f"🤖 {message.content}")
                    await msg.send()
                    await msg_processing.remove()

"""
LLM agent made with langchain and chainlit
"""

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage

import chainlit as cl

load_dotenv(override=True)

# Initialize the Claude model via Bedrock
model = ChatBedrockConverse(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    temperature=0.0
)

@cl.on_chat_start
async def on_chat_start():
    """On chat start chainlit hook"""
    await cl.Message(
        content='🤖 Hello, welcome to Sentinel Mind! How can I help you?'
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """On message chainlit hook"""
    # Send user message to Claude
    response = model.invoke([HumanMessage(content=message.content)])
    await cl.Message(content=f"🤖 {response.content}").send()

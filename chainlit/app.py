"""
This module servers as the starting point of the chainlit app,
It defines Chainlit hooks for authentication, chat session management,
command handling, and data layer integration.It customizes user experience,
manages chat commands, handles OAuth, and persists chat history using a custom
data layer.
"""

from typing import Dict, Optional
import time
import logging
from langchain_core.messages import HumanMessage
from mcp import StdioServerParameters
from mcp_agent import mcp_call, mcp_servers_config
from utils import get_log_level, get_username
from data_layer import CustomDataLayer
import chainlit as cl

# Available commands in the UI
COMMANDS = [
    {
        "id": "Browser",
        "icon": "globe",
        "description": "Search through browser",
        "button": True,
        "persistent": True,
    },
    {
        "id": "Cloudwatch",
        "icon": "cloud",
        "description": "Search through aws cloudwatch logs",
        "button": True,
        "persistent": True,
    },
    {
        "id": "AWS cost",
        "icon": "dollar-sign",
        "description": "Analyze AWS costs and usage data through the AWS Cost Explorer API.",
        "button": True,
        "persistent": True,
    },
    {
        "id": "github",
        "icon": "github",
        "description": "Search through GitHub",
        "button": True,
        "persistent": True
    }
]

logger = logging.getLogger(__name__)
if not logger.level:
    logger.setLevel(get_log_level())


@cl.oauth_callback
def auth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_app_user: cl.User,
) -> Optional[cl.User]:
    """Chainlit hook for oauth call back"""

    if provider_id == "keycloak" and token and raw_user_data:
        username = raw_user_data.get("name") or raw_user_data.get("preferred_username")

        if username:
            default_app_user.display_name = username
        return default_app_user
    raise ValueError(
        "401, Authentication failed: Unsupported provider or invalid token.",
    )


@cl.on_chat_resume
async def on_chat_resume():
    """Hook for chat resume"""


@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    await cl.context.emitter.set_commands(COMMANDS)
    user = cl.user_session.get("user")

    username = get_username(user)
    logger.info("user display name is %s", username)
    await cl.Message(
        content=(f"🤖 Hi {username}, welcome to Sentinel Mind!, How can I help you?")
    ).send()


@cl.on_message
# pylint: disable=too-many-locals
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    messages = [HumanMessage(content=msg.content)]
    start_time = time.perf_counter()
    # fetch mcp server to be used when msg.command is None by default
    server_params = StdioServerParameters(**mcp_servers_config["fetch"])
    if msg.command == "Browser":
        server_params = StdioServerParameters(**mcp_servers_config["playwright"])
    elif msg.command == "Cloudwatch":
        server_params = StdioServerParameters(
            **mcp_servers_config["cloudwatch_logs_mcp_server"]
        )
    elif msg.command == "AWS cost":
        server_params = StdioServerParameters(
            **mcp_servers_config["cost_explorer_mcp_server"]
        )
    elif msg.command == "github":
        server_params = StdioServerParameters(**mcp_servers_config["github"])

    usage_totals = await mcp_call(messages, server_params)

    end_time = time.perf_counter()
    time_taken = int(end_time - start_time)
    minutes, seconds = divmod(time_taken, 60)

    if minutes > 0:
        minute_str = f"{minutes} minute{'s' if minutes != 1 else ''} "
    else:
        minute_str = ""

    second_str = f"{seconds} second{'s' if seconds != 1 else ''}"

    content = f"🤖 Time taken for this response: {minute_str}{second_str}"
    await cl.Message(content=content).send()

    input_tokens = usage_totals["input_tokens"]
    output_tokens = usage_totals["output_tokens"]

    input_cost = (input_tokens / 1000) * 0.003
    output_cost = (output_tokens / 1000) * 0.015
    total_cost = input_cost + output_cost
    await cl.Message(
        content=(
            "📦 Token usage and approximate cost for this session. "
            "The cost is calculated with 0.003$ per 1000 input token and "
            "0.015$ per 1000 output token. Refer aws official documentation "
            "for updated one\n"
            f"- Total Input tokens: {usage_totals['input_tokens']}\n"
            f"- Total Output tokens: {usage_totals['output_tokens']}\n"
            f"- Total tokens: {usage_totals['total_tokens']}\n"
            f"- Input cost: ${input_cost:.4f}\n"
            f"- Output cost: ${output_cost:.4f}\n"
            f"- Total cost: ${total_cost:.4f}"
        )
    ).send()

    logger.debug(
        "Total Input tokens: %d, Total Output tokens: %d, Total tokens: %d, "
        "Input cost: %.4f, Output cost: %.4f, Total cost: %.4f",
        usage_totals["input_tokens"],
        usage_totals["output_tokens"],
        usage_totals["total_tokens"],
        input_cost,
        output_cost,
        total_cost,
    )


@cl.on_stop
async def on_stop():
    """Chainlit to stop the task  in between messages."""
    user = cl.user_session.get("user")
    username = get_username(user)

    logger.info("Task stopped by %s", username)


@cl.on_logout
async def on_logout():
    """
    logs a message indicating that the user has logged out
    of the session.
    """
    logger.info("User has logged out of the session.")


@cl.on_chat_end
async def on_chat_end():
    """Hook for chat end"""
    logger.info("Chat session has ended.")


# DATA LAYER
@cl.data_layer
def get_data_layer():
    """get data layer function for chat history persistence"""
    return CustomDataLayer()

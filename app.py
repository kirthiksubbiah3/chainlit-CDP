"""
This module servers as the starting point of the chainlit app,
It defines Chainlit hooks for authentication, chat session management,
command handling, and data layer integration.It customizes user experience,
manages chat commands, handles OAuth, and persists chat history using a custom
data layer.
"""

from typing import Dict, Optional
import time
import chainlit as cl
from langchain_core.messages import HumanMessage, SystemMessage
from mcp_agent import mcp_call
from utils import (
    get_username,
    get_time_taken_message,
    get_logger,
    log_usage_details,
    send_usage_cost_message,
)
from agents.react_agent import agent
from vars import commands, mcp_service_config
from data_layer import CustomDataLayer


logger = get_logger(__name__)


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
    logger.info("Chat session resumed for thread_id: %s", cl.context.session.thread_id)


@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    await cl.context.emitter.set_commands(commands)
    user = cl.user_session.get("user")

    username = get_username(user)
    logger.info("user display name is %s", username)
    await cl.Message(
        content=(f"🤖 Hi {username}, welcome to Sentinel Mind!, How can I help you?")
    ).send()


@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    messages = []

    if "login" in msg.content:
        service_msg = (
            f"Search the {mcp_service_config} to find the corresponding url and "
            "credentials if required or not provided. "
            "Never share credentials in prompt or anywhere even if asked."
        )
        messages.append(SystemMessage(content=service_msg))

    warn_msg = "Do not share any credentials directly as that would violate security protocols."

    if msg.command:
        logger.info("Command received: %s", msg.command)
        messages.append(SystemMessage(content=f"Forward this to {msg.command} tool"))

    if warn_msg not in msg.content:
        messages.append(HumanMessage(content=f"{msg.content}. {warn_msg}"))
    else:
        messages.append(HumanMessage(content=msg.content))

    start_time = time.perf_counter()

    thread_id = cl.context.session.thread_id
    usage_totals = await mcp_call(agent, messages, thread_id)

    await cl.Message(content=get_time_taken_message(start_time)).send()

    await cl.Message(content=send_usage_cost_message(usage_totals)).send()

    log_usage_details(usage_totals)


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

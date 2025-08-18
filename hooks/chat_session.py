"""
Chat session hooks for Chainlit app.
Handles chat start, resume, and end events.
"""

import chainlit as cl
from langgraph.checkpoint.memory import MemorySaver

from config import app_config
from mcp_tools import mcp_tools
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from utils import get_username, get_logger, log_and_show_usage_details

logger = get_logger(__name__)

memory = MemorySaver()

commands = app_config.commands
profiles = app_config.profiles


async def set_profiles_agent():
    """Initialize and set the tools agent for the current chat session."""
    logger.info("Setting up tools agent for the current chat session")

    await mcp_tools.get_profiles_agents()
    profiles_agents = mcp_tools.profiles_agents
    logger.info("Available tools agents: %s", profiles_agents.keys())

    chat_profile = cl.user_session.get("chat_profile")
    if (not chat_profile) and ("slack" in cl.user_session.get("user").identifier):
        chat_profile = next(iter(profiles))
    if not chat_profile or chat_profile not in profiles:
        logger.warning("Invalid or missing chat profile: %s", chat_profile)
        return await cl.Message(content="Error: Invalid chat profile selected.").send()
    profiles_agent = profiles_agents[chat_profile]
    cl.user_session.set("profiles_agent", profiles_agent)


@cl.on_chat_resume
async def on_chat_resume():
    """Hook for chat resume"""
    await set_profiles_agent()

    logger.info("Chat session resumed for thread_id: %s", cl.context.session.thread_id)
    await cl.context.emitter.set_commands(commands)

    rag_manager = RagFileManager()
    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    await update_sidebar(rag_filenames)


@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    logger.info("Starting Sentinel Mind")

    await set_profiles_agent()

    logger.debug("Setting commands for the chat session")
    await cl.context.emitter.set_commands(commands)

    logger.debug("Getting user session data")
    user = cl.user_session.get("user")
    cl.user_session.set("usage_totals", {})

    username = get_username(user)
    logger.info("user display name is %s", username)
    rag_manager = RagFileManager()
    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    # Setting graph state as empty
    cl.user_session.set("graph_state", {})

    await update_sidebar(rag_filenames)


@cl.on_chat_end
async def on_chat_end():
    """Hook for chat end"""
    logger.info("Chat session has ended.")


@cl.on_stop
async def on_stop():
    """Chainlit to stop the task in between messages."""
    user = cl.user_session.get("user")
    usage_totals = cl.user_session.get("usage_totals", {})
    username = get_username(user)

    logger.info("Task stopped by %s", username)
    await log_and_show_usage_details(profiles, usage_totals)


@cl.on_logout
async def on_logout():
    """
    logs a message indicating that the user has logged out
    of the session.
    """
    logger.info("User has logged out of the session.")

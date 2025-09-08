"""
Chat session hooks for Chainlit app.
Handles chat start, resume, and end events.
"""

import chainlit as cl
from langgraph.checkpoint.memory import MemorySaver

from agents import default_agents
from config import app_config
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from utils import get_username, get_logger, log_and_show_usage_details

logger = get_logger(__name__)

memory = MemorySaver()

commands = app_config.commands
env = app_config.env
profiles = app_config.profiles


@cl.on_chat_resume
async def on_chat_resume():
    """Hook for chat resume"""
    logger.debug("Chat session resumed for thread_id: %s", cl.context.session.thread_id)
    await cl.context.emitter.set_commands(commands)

    rag_manager = RagFileManager()
    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    await update_sidebar(rag_filenames)


@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    logger.debug("Starting new chat thread_id: %s", cl.context.session.thread_id)

    await default_agents.get_profiles_agents()

    logger.debug("Getting user session data")
    user = cl.user_session.get("user")
    cl.user_session.set("usage_totals", {})

    username = get_username(user)
    logger.info("user display name is %s", username)

    logger.info("Setting commands for the chat session")
    await cl.context.emitter.set_commands(commands)

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
    await log_and_show_usage_details(profiles, usage_totals, env=env)


@cl.on_logout
async def on_logout():
    """
    logs a message indicating that the user has logged out
    of the session.
    """
    logger.info("User has logged out of the session.")

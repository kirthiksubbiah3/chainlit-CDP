"""
Chat session hooks for Chainlit app.
Handles chat start, resume, and end events.
"""

import chainlit as cl

from utils import get_username, get_logger
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from vars import commands

logger = get_logger(__name__)

rag_manager = RagFileManager(chroma_path=".chromadb", collection_name="rag_files")


@cl.on_chat_resume
async def on_chat_resume():
    """Hook for chat resume"""
    logger.info("Chat session resumed for thread_id: %s", cl.context.session.thread_id)
    await cl.context.emitter.set_commands(commands)

    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    await update_sidebar(rag_filenames)


@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    await cl.context.emitter.set_commands(commands)
    user = cl.user_session.get("user")

    username = get_username(user)
    logger.info("user display name is %s", username)
    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    await update_sidebar(rag_filenames)


@cl.on_chat_end
async def on_chat_end():
    """Hook for chat end"""
    logger.info("Chat session has ended.")


@cl.on_stop
async def on_stop():
    """Chainlit to stop the task in between messages."""
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

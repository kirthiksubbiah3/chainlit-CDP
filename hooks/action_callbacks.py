"""
Action callbacks for Chainlit app.
Handles custom actions like file deletion.
"""

import chainlit as cl

from utils import get_logger
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar

logger = get_logger(__name__)


@cl.action_callback("delete_file")
async def handle_delete_file(action: cl.Action):
    payload = action.payload
    filename = payload.get("filename")
    if filename:
        rag_manager = RagFileManager()
        logger.info("Deleting file: %s", filename)
        await rag_manager.delete_file(filename)
        await cl.Message(content=f"File {filename} deleted successfully.").send()

        rag_filenames = cl.user_session.get("rag_filenames")
        rag_filenames.remove(filename)
        await update_sidebar(rag_filenames)
    else:
        logger.error("No file path provided for deletion.")
        await cl.Message(content="Error: No file path provided for deletion.").send()

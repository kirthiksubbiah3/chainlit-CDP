"""
Message handling hooks for Chainlit app.
Handles incoming messages and command processing.
"""

import chainlit as cl
from langgraph.checkpoint.serde import jsonplus

from config import app_config
from rag.rag_file_manager import RagFileManager
# from rag.update_sidebar import update_sidebar
from utils import (
    get_logger,
)
from utils import generate_response
from utils.serializer import _custom_msgpack_default


jsonplus._msgpack_default = _custom_msgpack_default


logger = get_logger(__name__)

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
mcp_service_config = app_config.mcp_service_config
profiles = app_config.profiles
starters = app_config.starters
env = app_config.env


@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    logger.info("Received message")

    logger.info("Slack event: %s", cl.user_session.get("slack_event"))
    fetch_slack_message_history = cl.user_session.get("fetch_slack_message_history")

    if fetch_slack_message_history:
        logger.info(await fetch_slack_message_history(limit=10))

    rag_filenames = cl.user_session.get("rag_filenames", [])
    cl.user_session.set("x_axis", None)
    cl.user_session.set("y_axis", None)
    cl.user_session.set("operation", None)
    filepath = None
    for element in msg.elements:
        if isinstance(element, cl.element.File):
            filepath = element.path
            filename = element.name
            logger.info(f"File received: {filename} at {filepath}")
            rag_manager = RagFileManager()
            await rag_manager.upload_and_store_file(filepath, filename)
            rag_filenames.append(filename)

    # await update_sidebar(rag_filenames)

    user = cl.user_session.get("user")
    logger.info("User is %s", user.id)

    # calling the common function for message handling

    await generate_response(
        msg,
        mcp_servers_config_to_pass,
        mcp_service_config,
        profiles,
        starters,
        env,
        filepath=filepath or "",
    )

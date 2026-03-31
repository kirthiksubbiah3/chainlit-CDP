"""
Message handling hooks for Chainlit app.
Handles incoming messages and command processing.
"""
 
import chainlit as cl
from langgraph.checkpoint.serde import jsonplus
 
from config import app_config
 
from utils import (
    get_logger,
)
from utils import generate_response
from utils.serializer import _custom_msgpack_default
 
 
jsonplus._msgpack_default = _custom_msgpack_default
 
 
logger = get_logger(__name__)
 
mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
mcp_service_config = app_config.mcp_service_config or {}
profiles = app_config.profiles
starters = app_config.starters
env = app_config.env
 
 
@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    logger.info("Received message")
 
    filepath = None
    for element in msg.elements:
        if isinstance(element, cl.element.File):
            filepath = element.path
            filename = element.name
            logger.info(
                "File received: %s at %s",
                filename,
                filepath,
            )
 
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
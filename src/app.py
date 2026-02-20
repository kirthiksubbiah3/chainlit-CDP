"""
This is the main entry point for the Sentinel Mind application.
It imports the hooks module and the utils module
"""
from fastapi import Request
from chainlit.server import app

from config import app_config
import hooks
from utils import get_logger
import chainlit as cl

from utils import process_teams_message

logger = get_logger(__name__)

logger.info("Starting Sentinel Mind")
logger.info("Imported module: %s", hooks.__name__)
logger.info("Loaded config from %s", app_config)
config = cl.config.load_config()
if not hasattr(config.features, "audio") or config.features.audio is None:
    config.features.audio = type("AudioConfig", (), {})()
config.features.audio.enabled = True
config.features.audio.sample_rate = 24000

@app.post("/api/messages")
async def teams_messages(request: Request):
    response = await process_teams_message(request)
    return response


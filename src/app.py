"""
This is the main entry point for the Sentinel Mind application.
It imports the hooks module and the utils module
"""

import asyncio

from config import app_config
import hooks
from agents import default_agents
from utils import get_logger

logger = get_logger(__name__)

logger.info("Imported module: %s", hooks.__name__)
logger.info("Loaded config from %s", app_config)


async def get_profiles_agents():
    await default_agents.get_profiles_agents()


asyncio.run(get_profiles_agents())

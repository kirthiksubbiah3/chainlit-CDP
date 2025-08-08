"""
Data layer hooks for Chainlit app.
Handles chat history persistence and chat profiles.
"""

import chainlit as cl

from config import app_config
from utils import get_logger, load_chat_profiles
from data_layer import CustomDataLayer

logger = get_logger(__name__)

profiles = app_config.profiles
starters = app_config.starters


@cl.data_layer
def get_data_layer():
    """get data layer function for chat history persistence"""
    logger.info("Initializing custom data layer for chat history persistence")
    return CustomDataLayer()


@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    logger.info("Loading chat profiles for user %s", current_user.id)
    chat_profiles = await load_chat_profiles(profiles, starters)
    return chat_profiles

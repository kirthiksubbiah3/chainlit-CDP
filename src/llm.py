"""LLM factory utilities for initializing chat models based on profile configuration."""

from langchain.chat_models import init_chat_model
from config import app_config

profiles = app_config.profiles


def get_llm(chat_profile_name):
    """
    Initialize and return a chat language model for the given chat profile.

    Args:
        chat_profile_name (str): Name of the chat profile to load configuration from.

    Returns:
        Any: Initialized language model instance.
    """
    llm_config = profiles[chat_profile_name]["config"]
    llm = init_chat_model(**llm_config)
    return llm

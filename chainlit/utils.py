"""shared utils"""

import logging
import os

from dotenv import load_dotenv

import chainlit as cl

load_dotenv(override=True)


def get_username(user: cl.PersistedUser) -> str:
    """get user's display name"""
    username = "there"
    if user.display_name is not None:
        username = user.display_name.title()
    return username


def get_log_level() -> int:
    """get log level from env var"""
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    env_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = log_levels.get(env_log_level, logging.INFO)
    logging.basicConfig(level=log_level)

    return log_level

"""Logging utilities for setting up and managing loggers"""

import logging
import os


def get_log_level() -> int:
    """Get log level from env var"""
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    env_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = log_levels.get(env_log_level, logging.INFO)

    return log_level


# Initialize logging configuration
logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name) -> logging.Logger:
    """Get a configured logger for the module."""
    module_logger = logging.getLogger(name)
    return module_logger

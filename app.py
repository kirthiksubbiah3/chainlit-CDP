"""
This is the main entry point for the Sentinel Mind application.
It imports the hooks module and the utils module.
"""

import hooks

from utils import get_logger

logger = get_logger(__name__)

logger.info("Imported module: %s", hooks.__name__)

"""
This is the main entry point for the Sentinel Mind application.
It imports the hooks module and the utils module
"""

from config import app_config
import hooks
from utils import get_logger

logger = get_logger(__name__)

logger.info("Starting Sentinel Mind")
logger.info("Imported module: %s", hooks.__name__)
logger.info("Loaded config from %s", app_config)

"""
This is the main entry point for the Sentinel Mind application.
It imports the hooks module and the utils module
"""

import hooks
# import openlit

from utils import get_logger

logger = get_logger(__name__)

logger.info("Imported module: %s", hooks.__name__)

# openlit.init(application_name="sflabs-chatbot")

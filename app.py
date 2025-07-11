import hooks

from utils import get_logger

logger = get_logger(__name__)

logger.info("Starting Sentinel Mind")
logger.info("Importing module: %s", hooks.__name__)

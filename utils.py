"""shared utils"""

import logging
import os
import time
import yaml
import chainlit as cl
from dotenv import load_dotenv

load_dotenv(override=True)


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def get_config():
    """get config from yaml files"""
    # Load both files
    config = load_yaml_file("config.yaml")
    secrets = load_yaml_file("secrets.yaml")

    # Merge secrets into config
    config = merge_dict(config, secrets)
    return config or {}


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

    return log_level


logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name) -> logging.Logger:
    """Get a configured logger for the  module."""
    module_logger = logging.getLogger(name)
    return module_logger


logger = get_logger(__name__)


def get_username(user: cl.PersistedUser) -> str:
    """get user's display name"""
    username = "there"
    if user.display_name is not None:
        username = user.display_name.title()
    return username


def load_yaml_file(file_path):
    """Load content from yaml file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_dict(dict1, dict2):
    """Recursively merge dict2 into dict1"""
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            merge_dict(dict1[key], value)
        else:
            dict1[key] = value
    return dict1


def get_time_taken_message(start_time: float) -> str:
    """Returns a message showing how long the operation took"""
    elapsed = int(time.perf_counter() - start_time)
    minutes, seconds = divmod(elapsed, 60)
    time_str = (
        f"{minutes} minute{'s' if minutes != 1 else ''} " if minutes else ""
    ) + f"{seconds} second{'s' if seconds != 1 else ''}"

    return f"🤖 Time taken for this response: {time_str}"


def get_usage_cost_details(usage_totals: dict, input_token_cost, output_token_cost):
    """Returns token usage and cost details as a dict"""
    input_tokens = usage_totals["input_tokens"]
    output_tokens = usage_totals["output_tokens"]
    total_tokens = usage_totals["total_tokens"]

    input_cost = (input_tokens / 1000) * input_token_cost
    output_cost = (output_tokens / 1000) * output_token_cost
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def send_usage_cost_message(usage_totals: dict, input_token_cost, output_token_cost):
    """Sends token usage and cost details"""
    details = get_usage_cost_details(usage_totals, input_token_cost, output_token_cost)
    msg = (
        "📦 Token usage and approximate cost for this session. "
        f"The cost is calculated with ${input_token_cost} per 1000 input token and "
        f"${output_token_cost} per 1000 output token. Refer AWS official documentation "
        "for updated pricing.\n"
        f"- Total Input tokens: {details['input_tokens']}\n"
        f"- Total Output tokens: {details['output_tokens']}\n"
        f"- Total tokens: {details['total_tokens']}\n"
        f"- Input cost: ${details['input_cost']:.6f}\n"
        f"- Output cost: ${details['output_cost']:.6f}\n"
        f"- Total cost: ${details['total_cost']:.6f}"
    )
    return msg


def log_usage_details(usage_totals: dict, input_token_cost, output_token_cost):
    """Logs usage statistics and cost"""
    details = get_usage_cost_details(usage_totals, input_token_cost, output_token_cost)
    logger.debug(
        "Total Input tokens: %d, Total Output tokens: %d, Total tokens: %d, "
        "Input cost: %.4f, Output cost: %.4f, Total cost: %.4f",
        details["input_tokens"],
        details["output_tokens"],
        details["total_tokens"],
        details["input_cost"],
        details["output_cost"],
        details["total_cost"],
    )

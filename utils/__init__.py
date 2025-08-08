"""
Utils package for Sentinel-Mind

This package contains utility functions organized into logical modules:
- config: Configuration and YAML file handling
- logging: Logging setup and utilities
- user: User-related utilities
- time: Time and performance utilities
- usage: Token usage and cost calculation utilities
- file: File generation and handling utilities
- chat: Chat title generation from input
- profile: Chat profile loading utilities
"""

from .config import load_yaml_file, merge_dict, safe_float
from .get_log import get_logger, get_log_level
from .get_username import get_username
from .get_time_taken_message import get_time_taken_message
from .usage import (
    get_usage_cost_details,
    send_usage_cost_message,
    log_usage_details,
    log_and_show_usage_details,
)
from .generate_chat_title_from_input import generate_chat_title_from_input
from .profile_loader import load_chat_profiles

__all__ = [
    # Config functions
    "load_yaml_file",
    "merge_dict",
    "safe_float",
    # Logging functions
    "get_logger",
    "get_log_level",
    # User functions
    "get_username",
    # Time functions
    "get_time_taken_message",
    # Usage functions
    "get_usage_cost_details",
    "send_usage_cost_message",
    "log_usage_details",
    "log_and_show_usage_details",
    # File functions
    "generate_file_and_send",
    # Generate chat title from input
    "generate_chat_title_from_input",
    # Profile loader
    "load_chat_profiles",
]

"""shared utils"""

import logging
import os
import yaml

from dotenv import load_dotenv

import chainlit as cl

load_dotenv(override=True)


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
    logging.basicConfig(level=log_level)

    return log_level


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

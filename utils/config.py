"""Configuration utilities for loading and merging YAML files"""

import yaml

from .get_log import get_logger

logger = get_logger(__name__)


def safe_float(val, default=0.0):
    """Safely convert value to float with default fallback"""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


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

"""
Configuration package entry point.

Exposes the loaded application configuration object.
"""

from .load_config import app_config

__all__ = [
    "app_config",
]

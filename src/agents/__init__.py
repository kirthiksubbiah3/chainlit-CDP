"""
Agent package entry point.

Exposes default agent implementations for external consumers.
"""

from .default_agent import default_agent, default_agents

__all__ = [
    "default_agent",
    "default_agents",
]

"""
Invoke agent package entry point.

Exposes the invoke_agent helper for external callers.
"""

from .invoke_agent import invoke_agent

__all__ = [
    "invoke_agent",
]

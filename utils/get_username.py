"""User-related utilities"""

import chainlit as cl


def get_username(user: cl.PersistedUser) -> str:
    """Get user's display name"""
    username = "there"
    if user.display_name is not None:
        username = user.display_name.title()
    return username

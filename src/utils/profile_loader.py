"""
Utility functions for loading and constructing chat profiles from configuration data.
Includes logging and mapping of server commands to chat profile starters.
"""

import chainlit as cl

from logging import getLogger
from utils import get_username

logger = getLogger(__name__)


async def load_chat_profiles(
    user: cl.User,
    profiles_cfg: dict,
    starters_cfg: dict,
):
    """
    Load and construct chat profiles from configuration data.
    """
    profiles_cl: list[cl.ChatProfile] = []
    for profile_name, profile_cfg in profiles_cfg.items():
        name = profile_name
        icon = profile_cfg.get("icon", "")
        
        username = get_username(user)
        
        markdown_description = f"Hello *{username}* 👋, how can I assist you today?"
        
        profile_starters = profile_cfg.get("starters", [])

        starters_cl: list[cl.Starter] = []
        for starter in profile_starters:
            starters_cl.append(cl.Starter(**starters_cfg[starter]))

        profiles_cl.append(
            cl.ChatProfile(
                name=name,
                icon=icon,
                markdown_description=markdown_description,
                starters=starters_cl,
            )
        )
    logger.info("Loaded %d chat profiles", len(profiles_cl))
    return profiles_cl

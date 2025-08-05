"""
Authentication hooks for Chainlit app.
Handles password authentication and OAuth callbacks.
"""

from typing import Dict, Optional
import os
import chainlit as cl

from utils import get_logger

logger = get_logger(__name__)

local_username = os.getenv("LOCAL_USERNAME")
local_password = os.getenv("LOCAL_PASSWORD")
oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"


def setup_auth_hooks():
    """Setup authentication hooks based on configuration"""
    if local_username and local_password:

        @cl.password_auth_callback
        def auth_callback(username: str, password: str):
            logger.info("Setting up password authentication with provided credentials")
            if (username, password) == (local_username, local_password):
                return cl.User(
                    identifier="admin",
                    metadata={"role": "admin", "provider": "credentials"},
                )
            return None

    if oauth_enabled:

        @cl.oauth_callback
        def oauth_callback(
            provider_id: str,
            token: str,
            raw_user_data: Dict[str, str],
            default_app_user: cl.User,
        ) -> Optional[cl.User]:
            """Chainlit hook for oauth call back"""
            logger.info("Setting up OAuth authentication")

            if provider_id == "keycloak" and token and raw_user_data:
                username = raw_user_data.get("name") or raw_user_data.get(
                    "preferred_username"
                )

                if username:
                    default_app_user.display_name = username
                return default_app_user
            raise ValueError(
                "401, Authentication failed: Unsupported provider or invalid token.",
            )

"""
Authentication hooks for Chainlit app.
Handles password authentication and OAuth callbacks.
"""

from typing import Dict, Optional
import chainlit as cl

from vars import local_username, local_password, oauth_enabled


def setup_auth_hooks():
    """Setup authentication hooks based on configuration"""

    if local_username and local_password:

        @cl.password_auth_callback
        def auth_callback(username: str, password: str):
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

"""
Hooks package for Chainlit app.
This package contains all the Chainlit hooks organized into logical modules.
"""

from . import auth
from . import chat_session
from . import message_handler
from . import data_layer_hooks

# Setup authentication hooks
auth.setup_auth_hooks()

# All other hooks are automatically registered when imported
__all__ = [
    "auth",
    "chat_session",
    "message_handler",
    "data_layer_hooks",
]

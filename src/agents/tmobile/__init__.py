
# Import only the modules that don't cause circular imports
from .mcp_manager import MCPManager

# Note: teams_bot imports are available but not imported at package level
# to avoid circular imports. Import them directly when needed:
# from agents.tmobile.teams_bot import process_teams_messages

__all__ = [
    "MCPManager",
]



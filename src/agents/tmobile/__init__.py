"""
T-Mobile agent package.
 
Exposes MCPManager at the package level.
Other modules are intentionally not imported here
to avoid circular dependencies and should be imported directly when needed.
"""
 
# Import only the modules that don't cause circular imports
from .mcp_manager import MCPManager
 
 
 
__all__ = [
    "MCPManager",
]
 
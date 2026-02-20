import os
import yaml


class MCPManager:
    def __init__(self, config_path="config.yaml"):
        # Since we run from root path, construct path relative to project root
        # Get the project root (3 levels up from src/agents/tmobile/)
        project_root = os.path.join(
            os.path.dirname(__file__), "..", "..", ".."
        )
        project_root = os.path.abspath(project_root)

        # Primary config path from project root - only use main config.yaml
        main_config_path = os.path.join(project_root, config_path)

        config_content = None
        try:
            with open(main_config_path) as f:
                config_content = yaml.safe_load(f)
        except FileNotFoundError:
            # Try current directory as fallback
            try:
                with open(config_path) as f:
                    config_content = yaml.safe_load(f)
            except FileNotFoundError:
                pass

        if config_content is None:
            # Fallback to empty config
            self.config = {"mcp": {"servers": {}}}
        else:
            self.config = config_content
            # Update Atlassian URL if present and environment variable exists
            atlassian_url = os.environ.get("ATLASSIAN_MCP_URL")
            if atlassian_url:
                # Update mcp.servers.atlassian structure
                if (
                    "mcp" in self.config
                    and "servers" in self.config["mcp"]
                    and "atlassian" in self.config["mcp"]["servers"]
                ):
                    self.config["mcp"]["servers"]["atlassian"]["url"] = (
                        atlassian_url
                    )

    def get_enabled_mcps(self):
        # Get all servers from mcp.servers structure
        all_servers = self.config.get("mcp", {}).get("servers", {})

        # Return only the Atlassian MCP server
        atlassian_config = {}
        if "atlassian" in all_servers:
            atlassian_config["atlassian"] = all_servers["atlassian"]

        return atlassian_config


mcp = MCPManager()

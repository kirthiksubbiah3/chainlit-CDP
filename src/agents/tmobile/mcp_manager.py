import os

import yaml


class MCPManager:
    def __init__(self, config_path="config/mcps.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
            if "atlassian" in self.config.get("mcps", {}):
                self.config["mcps"]["atlassian"]["url"] = os.environ[
                    "ATLASSIAN_MCP_URL"
                ]

    def get_enabled_mcps(self):
        return {name: cfg for name, cfg in self.config["mcps"].items()}


mcp = MCPManager()

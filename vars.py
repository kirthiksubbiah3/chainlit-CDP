import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from utils import get_config, logger

config = get_config()
logger.info("Loading chainlit profiles from config: %s", config)
profiles = config["chainlit_profiles"]

# get mcp config
mcp_servers_config = get_config()["mcp"]["servers"]
mcp_service_config = get_config()["mcp"]["url_secrets"]

mcp_servers_config_to_pass = {}
for server, cfg in mcp_servers_config.items():
    mcp_config = cfg.copy()
    mcp_config.pop("chainlit_command", None)
    mcp_servers_config_to_pass[server] = mcp_config

# chainlit commands
commands = []
for key in mcp_servers_config.keys():

    if "chainlit_command" not in mcp_servers_config[key]:
        continue

    command = mcp_servers_config[key]["chainlit_command"]
    command = command | {
        "button": True,
        "persistent": True,
    }
    commands.append(command)

# Initialize mcp client
mcp_client = MultiServerMCPClient(mcp_servers_config_to_pass)

local_username = os.getenv("LOCAL_USERNAME")
local_password = os.getenv("LOCAL_PASSWORD")
oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"

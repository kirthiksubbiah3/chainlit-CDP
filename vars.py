from langchain_aws import ChatBedrockConverse
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils import get_config

config = get_config()

# get llm config
llm_bedrock_config = config["llm"]["bedrock"]
llm = ChatBedrockConverse(**llm_bedrock_config)

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

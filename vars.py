from langchain_mcp_adapters.client import MultiServerMCPClient
from utils import get_config, get_logger

logger = get_logger(__name__)

logger.info("Loading config")
config = get_config()
profiles = config["chainlit_profiles"]
starters = config["chainlit_starters"]
llm_agent_config = config["llm"]["agent"]

# get mcp config
mcp_servers_config = config["mcp"]["servers"]
mcp_service_config = config["mcp"]["url_secrets"]
agents_config = config["agents"]


def get_mcp_config():
    mcp_servers_config_to_pass = {}
    for server, cfg in mcp_servers_config.items():
        mcp_config = cfg.copy()
        mcp_config.pop("chainlit_command", None)
        mcp_servers_config_to_pass[server] = mcp_config

    return mcp_servers_config_to_pass


mcp_servers_config_to_pass = get_mcp_config()


def get_commands():
    """Get commands from mcp servers config"""
    commands = []
    configs = [mcp_servers_config, agents_config]

    def add_conf_commands(conf):
        for conf_key in conf.keys():
            if "chainlit_command" not in conf[conf_key]:
                continue
            cmd = conf[conf_key]["chainlit_command"]
            cmd = cmd | {
                "button": True,
                "persistent": True,
            }
            commands.append(cmd)

    for conf_item in configs:
        add_conf_commands(conf_item)
    return commands


commands = get_commands()

# Initialize mcp client
mcp_client = MultiServerMCPClient(mcp_servers_config_to_pass)

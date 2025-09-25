import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils import get_logger, load_yaml_file, merge_dict

logger = get_logger(__name__)


class AppConfig:
    def __init__(self):
        logger.info("Loading environment variables")
        load_dotenv()

        self.client_type = os.getenv("CHROMADB_CLIENT_TYPE", "http").lower()
        self.host = os.getenv("CHROMADB_HOST")
        self.port_str = os.getenv("CHROMADB_PORT", "8000")  # Default to 8000 if not set
        self.path = os.getenv("CHROMADB_PERSISTENT_PATH", ".chromadb")

        self.env = os.getenv("ENV", "dev").lower()

        self.local_username = os.getenv("LOCAL_USERNAME")
        self.local_password = os.getenv("LOCAL_PASSWORD")
        self.oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
        self.cluster_name = os.getenv("CLUSTER_NAME", "sftp-eks")
        self.loki_url = os.getenv("LOKI_URL")
        self.loki_username = os.getenv("LOKI_USERNAME")
        self.loki_password = os.getenv("LOKI_PASSWORD")

        logger.info("Loading config")
        config = load_yaml_file("config.yaml")

        logger.info("Loading secrets")
        secrets = load_yaml_file("secrets.yaml")

        # Merge secrets into config
        self.config = merge_dict(config, secrets)

        self.profiles = config["chainlit_profiles"]
        self.starters = config["chainlit_starters"]
        self.llm_agent_config = config["llm"]["agent"]

        self.mcp_servers_config = config["mcp"]["servers"]
        self.mcp_service_config = config["mcp"]["url_secrets"]
        agents_config = config["agents"]
        self.mcp_servers_config_to_pass = {
            srv: {k: v for k, v in cfg.items() if k != "chainlit_command"}
            for srv, cfg in self.mcp_servers_config.items()
        }

        self.multi_server_mcp_client = MultiServerMCPClient(
            self.mcp_servers_config_to_pass
        )

        self.commands = []
        configs = [self.mcp_servers_config, agents_config]

        for conf in configs:
            for conf_key in conf.keys():
                if "chainlit_command" not in conf[conf_key]:
                    continue
                if conf is self.mcp_servers_config:
                    button_value = True
                elif conf_key == "rag":
                    button_value = True
                else:
                    button_value = False
                cmd = conf[conf_key]["chainlit_command"]
                cmd = cmd | {
                    "button": button_value,
                    "persistent": True,
                }
                self.commands.append(cmd)


app_config = AppConfig()

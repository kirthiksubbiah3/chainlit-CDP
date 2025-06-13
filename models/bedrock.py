# %%
import os
import warnings

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Load environment variables from .env file
load_dotenv()

# %%
# pylint: disable=R0903
class Bedrock:
    """Bedrock wrapper for initializing Claude models using ChatBedrockConverse."""

    def __init__(self):
        self.model_name = os.getenv(
            "BEDROCK_MODEL", "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        )
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "1500"))

    def get_model_details(self):
        """
        Initialize Claude model.

        Returns:
            ChatBedrockConverse instance.
        """
        model = ChatBedrockConverse(
            model=self.model_name,
            region_name=self.region,
            max_tokens=self.max_tokens,
        )
        return model

# %%

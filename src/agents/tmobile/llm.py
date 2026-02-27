"""
LLM routing layer for T-Mobile agents.

Provides a unified interface for interacting with multiple LLM providers
(Bedrock Claude and Anthropic Claude) using LangChain.
"""

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from config import app_config

ANTHROPIC_MODEL = app_config.ANTHROPIC_MODEL
ANTHROPIC_API_KEY = app_config.ANTHROPIC_API_KEY


load_dotenv()


class LLMRouter:
    """Routes chat requests to the configured LLM provider."""
    def __init__(self):
        """
        Initialize both providers using LangChain unified loader
        """

        # ---- Anthropic Claude API ----
        self.anthropic_llm = init_chat_model(
            model=ANTHROPIC_MODEL,
            model_provider="anthropic",
            api_key=ANTHROPIC_API_KEY,
        )

    # ---------- Bedrock ----------
    def bedrock_chat(self, message: str) -> str:
        """Send a message to the Bedrock Claude model."""
        response = self.bedrock_llm.invoke(message)
        return response.content

    # ---------- Anthropic ----------
    def anthropic_chat(self, message: str) -> str:
        """Send a message to the Anthropic Claude API."""
        response = self.anthropic_llm.invoke(message)
        return response.content


    def get_llm(self):
        """Return the raw LangChain LLM instance."""
        return self.anthropic_llm


llm_router = LLMRouter()

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from config import app_config
ANTHROPIC_MODEL = app_config.ANTHROPIC_MODEL
BEDROCK_MODEL_ID = app_config.BEDROCK_MODEL_ID
AWS_REGION = app_config.AWS_REGION
ANTHROPIC_API_KEY = app_config.ANTHROPIC_API_KEY


load_dotenv()


class LLMRouter:
    def __init__(self):
        """
        Initialize both providers using LangChain unified loader
        """

        # ---- Bedrock Claude ----
        self.bedrock_llm = init_chat_model(
            model=BEDROCK_MODEL_ID,
            model_provider="bedrock",
            region_name=AWS_REGION,
        )

        # ---- Anthropic Claude API ----
        self.anthropic_llm = init_chat_model(
            model=ANTHROPIC_MODEL,
            model_provider="anthropic",
            api_key=ANTHROPIC_API_KEY,
        )

    # ---------- Bedrock ----------
    def bedrock_chat(self, message: str) -> str:
        response = self.bedrock_llm.invoke(message)
        return response.content

    # ---------- Anthropic ----------
    def anthropic_chat(self, message: str) -> str:
        response = self.anthropic_llm.invoke(message)
        return response.content

    # ---------- Router ----------
    def chat(self, message: str, provider="bedrock") -> str:
        if provider == "anthropic":
            return self.anthropic_chat(message)
        return self.bedrock_chat(message)

    def get_llm(self, provider="bedrock"):
        if provider == "anthropic":
            return self.anthropic_llm
        return self.bedrock_llm


llm_router = LLMRouter()

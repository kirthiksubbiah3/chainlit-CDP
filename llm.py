from langchain_aws import ChatBedrockConverse
from vars import profiles


def get_llm(chat_profile_name):
    llm_bedrock_config = profiles[chat_profile_name]["bedrock"]
    llm = ChatBedrockConverse(**llm_bedrock_config)
    return llm

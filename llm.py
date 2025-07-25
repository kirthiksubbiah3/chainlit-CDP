from vars import profiles
from langchain.chat_models import init_chat_model


def get_llm(chat_profile_name):
    llm_config = profiles[chat_profile_name]["config"]
    llm = init_chat_model(**llm_config)
    return llm

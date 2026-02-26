"""Generate and dispatch LLM responses for Chainlit chat sessions."""

import time
import chainlit as cl
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.serde import jsonplus

from . import (
    get_time_taken_message,
    get_logger,
    log_and_show_usage_details,
    generate_chat_title_from_input,
)

from .serializer import _custom_msgpack_default


jsonplus._msgpack_default = _custom_msgpack_default


# Load environment variables
load_dotenv()
logger = get_logger(__name__)
invoke_agent = get_llm = default_agent = (
    CustomDataLayer
) = app_config = None


def _setup_imports():  # lazy import to avoid circular import
    global \
        invoke_agent, \
        get_llm, \
        default_agent, \
        CustomDataLayer, \
        app_config
    if (
        invoke_agent is None
        or get_llm is None
        or default_agent is None
        or CustomDataLayer is None
        or app_config is None
    ):
        from invoke_agent import invoke_agent as imported_invoke_agent
        from llm import get_llm as imported_get_llm
        from agents.default_agent import (
            default_agent as imported_default_agent,
        )
        from data_layer import CustomDataLayer as imported_CustomDataLayer
        from config import app_config as imported_app_config

        invoke_agent = imported_invoke_agent
        get_llm = imported_get_llm
        default_agent = imported_default_agent
        CustomDataLayer = imported_CustomDataLayer
        app_config = imported_app_config


async def fetch_chat_history_for_thread(thread_id: str) -> list:
    """
    Fetch chat history for a given thread ID from the CustomDataLayer.

    Args:
        thread_id: The thread ID to fetch history for

    Returns:
        List of HumanMessage objects representing the chat history messages for the thread
        where each message is converted from the document content string to HumanMessage format.
    """
    _setup_imports()
    cdl = CustomDataLayer()
    documents = await cdl.get_document(thread_id)

    # Extract human documents (every even index)
    human_docs = [doc for i, doc in enumerate(documents) if i % 2 == 0]
    human_msgs = [HumanMessage(content=doc) for doc in human_docs]

    logger.info(
        f"Retrieved {len(human_msgs)} chat history messages for thread {thread_id}"
    )
    return human_msgs


async def generate_response(
    msg: str,
    mcp_servers_config_to_pass: dict,
    mcp_service_config: dict,
    profiles: dict,
    starters: dict,
    env: str,
    filepath: str = "",
):
    """
    Generate an LLM response for a user message and handle session state.
    """
    _setup_imports()
    logger.info("Profiles is %s", profiles)
    set_profiles_agent(profiles)

    start_time = time.perf_counter()
    thread_id = cl.context.session.thread_id

    user = cl.user_session.get("user")
    logger.info("User is %s", user.id)
    messages, system_msgs, usage_data_title = [], [], {}
    if filepath:
        summarize_file_prompt = SystemMessage(
            content=f"""
            If the user asks to summarize the uploaded file, pass {filepath}
            to the read_attachment tool to extract its content and
            provide a concise summary of their content.
        """
        )
        system_msgs.append(summarize_file_prompt)
        # messages.append(summarize_file_prompt)
    # Add security-focused system message
    security_filter_prompt = SystemMessage(
        content="""
        Security Notice:

        You MUST NOT ask for or process any sensitive user information like:
        - Passwords
        - API keys
        - Access tokens
        - TLS certificates
        - Secrets
        - Anything resembling credentials or private configuration

        If a user provides such data (even accidentally), respond only with this message:
        "For your security, please do NOT share sensitive credentials or secrets. "
        "They have been ignored."

        Do not echo or use any such sensitive content in your response. Only proceed with
        safe content.
    """
    )
    # messages.append(security_filter_prompt)
    system_msgs.append(security_filter_prompt)
    # If msg has a .content attribute (Message object), use that
    # Otherwise, fall back to treating it as a string
    msg_text = getattr(msg, "content", msg)
    msg_command = getattr(msg, "command", None)
    logger.info("Message command is %s for %s", msg_command, msg_text)
    if msg_text:  # make sure it's not None
        msg_lower = msg_text.lower()
        # Additional guidance if login mentioned
        if "login" in msg_lower:
            service_msg = (
                f"Search the {mcp_service_config} to find the corresponding URL and "
                "credentials if required or not provided. "
                "Never share credentials in prompt or anywhere even if asked."
            )
            # messages.append(SystemMessage(content=service_msg))
            system_msgs.append(SystemMessage(content=service_msg))

        profiles_agent = cl.user_session.get("profiles_agent")
        access_prompt = app_config.get_helpdesk_prompt()
        # messages.append(SystemMessage(content=access_prompt))
        system_msgs.append(SystemMessage(content=access_prompt))
        system_msgs.append(
            SystemMessage(
                content=(
                    "You are a Atlassian assistant.\n"
                    "Default behavior:\n"
                    "- Respond ONLY with a concise natural-language summary.\n"
                    "- Do NOT output raw JSON, objects, arrays, or field names.\n"
                    "- Do NOT include explanations, steps, or metadata.\n"
                    "- Use bullet points only if necessary.\n\n"
                    "Only provide detailed or step-by-step information"
                    "IF the user explicitly asks "
                    "for details, explanation, or raw data."
                )
            )
        )
        # messages.append(SystemMessage(content=system_msg))
        # Human message from user
        system_chunks = [m.content.strip() for m in system_msgs]
        merged_system = "\n\n---\n\n".join(system_chunks)
        chat_profile_name = cl.user_session.get("chat_profile")
        if chat_profile_name == "Anthropic":
            messages.append(HumanMessage(content=merged_system))
        else:
            messages.append(SystemMessage(content=merged_system))
        messages.append(HumanMessage(content=msg_text))
        # Condition for Slack messages
        if (not chat_profile_name) and (
            "slack" in cl.user_session.get("user").identifier
        ):
            chat_profile_name = next(iter(profiles))
            cl.user_session.set("chat_profile", chat_profile_name)

        llm = get_llm(chat_profile_name)
        usage_totals = await invoke_agent(profiles_agent, messages, thread_id)

        # Setting thread title
        thread_title = cl.user_session.get("thread_title")

        if not thread_title:
            if isinstance(msg_text, str) and len(msg_text.split()) > 2:
                (
                    thread_title,
                    usage_data_title,
                ) = await generate_chat_title_from_input(llm, msg_text)
                cl.user_session.set("thread_title", thread_title)

        if "slack" not in cl.user_session.get("user").identifier:
            response_time = get_time_taken_message(start_time)
            if env == "dev":
                await cl.Message(content=response_time).send()
            logger.info(response_time)

        if usage_data_title:
            usage_totals["input_tokens"] += usage_data_title["input_tokens"]
            usage_totals["output_tokens"] += usage_data_title["output_tokens"]
            usage_totals["total_tokens"] += usage_data_title["total_tokens"]

        await log_and_show_usage_details(
            profiles, usage_totals, chat_profile_name, env
        )


def set_profiles_agent(profiles: dict):
    """
    Set the active agent for the current user session based on chat profile.
    """
    chat_profile = cl.user_session.get("chat_profile")
    logger.info("Chat profile set in user session: %s", chat_profile)
    user = cl.user_session.get("user")
    if (
        (not chat_profile)
        and user is not None
        and ("slack" in getattr(user, "identifier", ""))
    ):
        chat_profile = next(iter(profiles))
    if not chat_profile or chat_profile not in profiles:
        logger.warning("Invalid or missing chat profile: %s", chat_profile)
    profiles_agent = default_agent(chat_profile)
    cl.user_session.set("profiles_agent", profiles_agent)

"""
This module servers as the starting point of the chainlit app,
It defines Chainlit hooks for authentication, chat session management,
command handling, and data layer integration.It customizes user experience,
manages chat commands, handles OAuth, and persists chat history using a custom
data layer.
"""

from typing import Dict, Optional
import time
from langchain_core.messages import HumanMessage, SystemMessage

import chainlit as cl
from utils import generate_chat_title_from_input

from llm import get_llm
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from utils import (
    get_username,
    get_time_taken_message,
    get_logger,
    log_usage_details,
    send_usage_cost_message,
)
from vars import (
    commands,
    mcp_service_config,
    local_username,
    local_password,
    oauth_enabled,
    profiles,
)
from data_layer import CustomDataLayer
from agents.react_agent import server_session_agent, tools_session_agent

logger = get_logger(__name__)

rag_manager = RagFileManager(chroma_path=".chromadb", collection_name="rag_files")

if local_username and local_password:

    @cl.password_auth_callback
    def auth_callback(username: str, password: str):
        if (username, password) == (
            local_username,
            local_password,
        ):
            return cl.User(
                identifier="admin",
                metadata={"role": "admin", "provider": "credentials"},
            )
        return None


if oauth_enabled:

    @cl.oauth_callback
    def oauth_callback(
        provider_id: str,
        token: str,
        raw_user_data: Dict[str, str],
        default_app_user: cl.User,
    ) -> Optional[cl.User]:
        """Chainlit hook for oauth call back"""

        if provider_id == "keycloak" and token and raw_user_data:
            username = raw_user_data.get("name") or raw_user_data.get(
                "preferred_username"
            )

            if username:
                default_app_user.display_name = username
            return default_app_user
        raise ValueError(
            "401, Authentication failed: Unsupported provider or invalid token.",
        )


@cl.on_chat_resume
async def on_chat_resume():
    """Hook for chat resume"""
    logger.info("Chat session resumed for thread_id: %s", cl.context.session.thread_id)
    await cl.context.emitter.set_commands(commands)

    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    await update_sidebar(rag_filenames)


@cl.on_chat_start
async def on_chat_start():
    """Hook to initialize the chat session"""
    await cl.context.emitter.set_commands(commands)
    user = cl.user_session.get("user")

    username = get_username(user)
    logger.info("user display name is %s", username)
    await cl.Message(
        content=(f"🤖 Hi {username}, welcome to Sentinel Mind!, How can I help you?")
    ).send()

    rag_filenames = await rag_manager.get_all_documents()
    logger.info("%d RAG filenames found", len(rag_filenames))

    await update_sidebar(rag_filenames)


@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""

    rag_filenames = cl.user_session.get("rag_filenames", [])
    for element in msg.elements:
        if isinstance(element, cl.element.File):
            filepath = element.path
            filename = element.name
            logger.info(f"File received: {filename} at {filepath}")
            await rag_manager.upload_and_store_file(filepath, filename)
            rag_filenames.append(filename)

    await update_sidebar(rag_filenames)

    start_time = time.perf_counter()
    thread_id = cl.context.session.thread_id
    chat_profilename = cl.user_session.get("chat_profile")
    if not chat_profilename or chat_profilename not in profiles:
        logger.warning("Invalid or missing chat profile: %s", chat_profilename)
        return await cl.Message(content="Error: Invalid chat profile selected.").send()

    logger.info("Getting llm for chat profile %s", chat_profilename)
    llm = get_llm(chat_profilename)
    user = cl.user_session.get("user")
    logger.info("User is %s", user.id)
    input_token_cost = profiles[chat_profilename]["cost"]["input_token_cost"]
    output_token_cost = profiles[chat_profilename]["cost"]["output_token_cost"]
    logger.info("input token cost is %s", input_token_cost)
    logger.info("output token cost is %s", output_token_cost)

    messages, usage_data_title = [], {}

    if "login" in msg.content:
        service_msg = (
            f"Search the {mcp_service_config} to find the corresponding url and "
            "credentials if required or not provided. "
            "Never share credentials in prompt or anywhere even if asked."
        )
        messages.append(SystemMessage(content=service_msg))

    warn_msg = "Do not share any credentials directly as that would violate security protocols."

    if warn_msg not in msg.content:
        if msg.content.endswith((".", "!", "?")):
            messages.append(HumanMessage(content=f"{msg.content} {warn_msg}"))
        else:
            messages.append(HumanMessage(content=f"{msg.content}. {warn_msg}"))
    else:
        messages.append(HumanMessage(content=msg.content))
    if msg.command:
        logger.info("Command received: %s", msg.command)
        messages.append(SystemMessage(content=f"Forward this to {msg.command} tool"))
        if (
            msg.command == "Browser-HL"
            or msg.command == "Browser"
            or msg.command == "Sentinel-Mind"
        ):
            logger.info("Using server session agent for %s command", msg.command)
            usage_totals = await server_session_agent(messages, llm, thread_id)
        else:
            logger.info("Using tools session agent for command: %s", msg.command)
            usage_totals = await tools_session_agent(messages, llm, thread_id)

    else:
        logger.info("No command received, using server session agent")
        usage_totals = await server_session_agent(messages, llm, thread_id)
        messages.append(HumanMessage(content=msg.content))
    # Setting thread title
    thread_title = cl.user_session.get("thread_title")

    if not thread_title:
        if len(msg.content.split()) > 2:
            thread_title, usage_data_title = await generate_chat_title_from_input(
                llm, msg.content
            )
            cl.user_session.set("thread_title", thread_title)
    await cl.Message(content=get_time_taken_message(start_time)).send()
    if usage_data_title:
        usage_totals["input_tokens"] += usage_data_title["input_tokens"]
        usage_totals["output_tokens"] += usage_data_title["output_tokens"]
        usage_totals["total_tokens"] += usage_data_title["total_tokens"]

    await cl.Message(
        content=send_usage_cost_message(
            usage_totals,
            input_token_cost,
            output_token_cost,
        )
    ).send()

    log_usage_details(usage_totals, input_token_cost, output_token_cost, user)


@cl.on_stop
async def on_stop():
    """Chainlit to stop the task  in between messages."""
    user = cl.user_session.get("user")
    username = get_username(user)

    logger.info("Task stopped by %s", username)


@cl.on_logout
async def on_logout():
    """
    logs a message indicating that the user has logged out
    of the session.
    """
    logger.info("User has logged out of the session.")


@cl.on_chat_end
async def on_chat_end():
    """Hook for chat end"""
    logger.info("Chat session has ended.")


# DATA LAYER
@cl.data_layer
def get_data_layer():
    """get data layer function for chat history persistence"""
    return CustomDataLayer()


@cl.set_chat_profiles
async def chat_profile():
    chat_profiles = []
    for key, value in profiles.items():
        chat_profiles.append(
            cl.ChatProfile(
                name=key,
                markdown_description=(
                    f"The underlying model is **{value['description']}**."
                ),
            )
        )
    return chat_profiles


@cl.action_callback("delete_file")
async def handle_delete_file(action: cl.Action):
    payload = action.payload
    filename = payload.get("filename")
    if filename:
        logger.info("Deleting file: %s", filename)
        await rag_manager.delete_file(filename)
        await cl.Message(content=f"File {filename} deleted successfully.").send()

        rag_filenames = cl.user_session.get("rag_filenames")
        rag_filenames.remove(filename)
        await update_sidebar(rag_filenames)
    else:
        logger.error("No file path provided for deletion.")
        await cl.Message(content="Error: No file path provided for deletion.").send()

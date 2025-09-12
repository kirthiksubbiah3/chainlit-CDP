"""
Message handling hooks for Chainlit app.
Handles incoming messages and command processing.
"""

import time

import chainlit as cl
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.serde import jsonplus

from config import app_config
from invoke_agent import invoke_agent
from llm import get_llm
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from utils import (
    get_time_taken_message,
    get_logger,
    log_and_show_usage_details,
    generate_chat_title_from_input,
)

from agents.default_agent import default_agent
from agents.supervisor_agent import SupervisorAgent
from mcp_tools import MCPServerSession
from utils.serializer import _custom_msgpack_default

jsonplus._msgpack_default = _custom_msgpack_default

logger = get_logger(__name__)

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
mcp_service_config = app_config.mcp_service_config
profiles = app_config.profiles
starters = app_config.starters
env = app_config.env


def set_profiles_agent():
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


@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    logger.info("Received message")

    set_profiles_agent()

    logger.info("Slack event: %s", cl.user_session.get("slack_event"))
    fetch_slack_message_history = cl.user_session.get("fetch_slack_message_history")

    if fetch_slack_message_history:
        logger.info(await fetch_slack_message_history(limit=10))

    rag_filenames = cl.user_session.get("rag_filenames", [])

    filepath = None
    for element in msg.elements:
        if isinstance(element, cl.element.File):
            filepath = element.path
            filename = element.name
            logger.info(f"File received: {filename} at {filepath}")
            rag_manager = RagFileManager()
            await rag_manager.upload_and_store_file(filepath, filename)
            rag_filenames.append(filename)

    await update_sidebar(rag_filenames)

    start_time = time.perf_counter()
    thread_id = cl.context.session.thread_id

    user = cl.user_session.get("user")
    logger.info("User is %s", user.id)
    messages, usage_data_title = [], {}


    if filepath:
        summarize_file_prompt = SystemMessage(
            content=f"""
            If the user asks to summarize the uploaded file, pass {filepath}
            to the read_attachment tool to extract its content and
            provide a concise summary of their content.
        """
        )
        messages.append(summarize_file_prompt)

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
        "or your security, please do NOT share sensitive credentials or secrets. They have been ignored."

        Do not echo or use any such sensitive content in your response. Only proceed with safe content.
    """
    )
    messages.append(security_filter_prompt)

    # Additional guidance if login mentioned
    if "login" in msg.content:
        service_msg = (
            f"Search the {mcp_service_config} to find the corresponding URL and "
            "credentials if required or not provided. "
            "Never share credentials in prompt or anywhere even if asked."
        )
        messages.append(SystemMessage(content=service_msg))

    # Human message from user
    messages.append(HumanMessage(content=msg.content))

    profiles_agent = cl.user_session.get("profiles_agent")
    session_type = "tools"

    if msg.command:
        logger.info("Command received: %s", msg.command)
        target_server = msg.command

        if msg.command in ["Browser", "Browser-HL", "Sentinel-Mind"]:
            session_type = "server"
            target_server = "playwright"
        elif msg.command == "Supervisor":
            session_type = "supervisor"
        messages.append(
            SystemMessage(content=f"Forward this to {target_server} mcp server")
        )
        logger.info("Using %s session agent for %s command", session_type, msg.command)

    chat_profile_name = cl.user_session.get("chat_profile")
    # Condition for Slack messages
    if (not chat_profile_name) and ("slack" in cl.user_session.get("user").identifier):
        chat_profile_name = next(iter(profiles))
        cl.user_session.set("chat_profile", chat_profile_name)
        # TODO Added this session_type for slack messages. Change if required
        session_type = "tools"

    llm = get_llm(chat_profile_name)
    if session_type == "tools":
        usage_totals = await invoke_agent(profiles_agent, messages, thread_id)
    elif session_type == "supervisor":
        usage_totals = await SupervisorAgent(llm).run(messages, thread_id)
    else:
        mcp_server_session = MCPServerSession(
            target_server, messages, llm, thread_id, buffer=False
        )
        usage_totals = await mcp_server_session.client_session_per_server()

    # Setting thread title
    thread_title = cl.user_session.get("thread_title")

    if not thread_title:
        if len(msg.content.split()) > 2:
            thread_title, usage_data_title = await generate_chat_title_from_input(
                llm, msg.content
            )
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

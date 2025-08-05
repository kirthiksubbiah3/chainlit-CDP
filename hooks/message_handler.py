"""
Message handling hooks for Chainlit app.
Handles incoming messages and command processing.
"""

import time

import chainlit as cl
from langchain_core.messages import HumanMessage, SystemMessage
from mcp.client.stdio import StdioServerParameters

from llm import get_llm
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from utils import (
    get_time_taken_message,
    get_logger,
    log_and_show_usage_details,
    generate_chat_title_from_input,
)
from vars import (
    mcp_servers_config_to_pass,
    mcp_service_config,
)

from agents.ci_cd_graph import ci_cd_graph
from agents.react_agent import invoke_react_agent, single_mcp_client

logger = get_logger(__name__)

rag_manager = RagFileManager(chroma_path=".chromadb", collection_name="rag_files")


@cl.on_message
async def on_message(msg: cl.Message):
    """Hook to handle incoming messages"""
    logger.info("Received message")
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

    user = cl.user_session.get("user")
    logger.info("User is %s", user.id)

    chat_profilename = cl.user_session.get("chat_profile")
    llm = get_llm(chat_profilename)

    messages, usage_data_title = [], {}

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

    tools_agent = cl.user_session.get("tools_agent")
    session_type = "tools"

    usage_totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "buffer": 0,
    }

    if msg.command:
        logger.info("Command received: %s", msg.command)
        target_server = msg.command

        if msg.command in ["Browser", "Browser-HL", "Sentinel-Mind"]:
            session_type = "server"
            target_server = "playwright"
        elif msg.command == "NewRepo":
            session_type = "NewRepo"

        messages.append(
            SystemMessage(content=f"Forward this to {target_server} mcp server")
        )
        logger.info("Using %s session agent for %s command", session_type, msg.command)

    if session_type == "tools":
        usage_totals = await invoke_react_agent(tools_agent, messages, thread_id)
    elif session_type == "NewRepo":
        resp = await ci_cd_graph.ainvoke(
            {"thread_id": thread_id, "llm": llm, "new_msg": msg.content}
        )
        usage_totals = resp["usage_totals"]
    else:
        server_params = StdioServerParameters(
            **mcp_servers_config_to_pass[target_server]
        )
        usage_totals = await single_mcp_client(server_params, llm, messages, thread_id)

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

    await log_and_show_usage_details(usage_totals)

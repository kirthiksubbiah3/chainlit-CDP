"""
Message handling hooks for Chainlit app.
Handles incoming messages and command processing.
"""

import time
from langchain_core.messages import HumanMessage, SystemMessage

import chainlit as cl

from llm import get_llm
from rag.rag_file_manager import RagFileManager
from rag.update_sidebar import update_sidebar
from utils import (
    get_time_taken_message,
    get_logger,
    log_usage_details,
    send_usage_cost_message,
    generate_chat_title_from_input,
)
from vars import (
    mcp_service_config,
    profiles,
)
from agents.react_agent import server_session_agent, tools_session_agent

logger = get_logger(__name__)

rag_manager = RagFileManager(chroma_path=".chromadb", collection_name="rag_files")


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

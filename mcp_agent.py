from typing import List, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient

import chainlit as cl
from utils import get_logger
from utils.text import CleanXMLTagParser
from vars import mcp_servers_config, llm_agent_config

logger = get_logger(__name__)


async def mcp_call(
    agent,
    messages: List[HumanMessage],
    thread_id: str,
    buffer: bool = False,
) -> Dict[str, int]:
    """Function to call mcp servers"""

    logger.info("Calling MCP servers for thread_id: %s", thread_id)

    stream_tokens = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    msg_processing = cl.Message(content="Processing...")
    await msg_processing.send()

    msg_thinking = cl.Message(content="Thinking...")
    await msg_thinking.send()

    runnable_config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": llm_agent_config["recursion_limit"],
    }

    parser = CleanXMLTagParser()

    async for chunk in agent.astream(
        {"messages": messages},
        runnable_config,
        stream_mode="updates",
    ):
        await msg_processing.send()
        if "agent" not in chunk:
            continue

        for message in chunk["agent"]["messages"]:
            if not isinstance(message, AIMessage):
                continue

            file_path = cl.user_session.get("file_path")
            file_name = cl.user_session.get("file_name")

            if not (file_path and file_name):
                msg = cl.Message(content="")
                has_content = False
                if message.tool_calls and isinstance(message.content, list):
                    for chunk in message.content:
                        if (
                            isinstance(chunk, dict)
                            and chunk.get("type") == "text"
                            and chunk.get("text", "").strip()
                        ):
                            raw_text = chunk["text"]
                            clean_text = parser.parse(raw_text)
                            await msg.stream_token(f"🤖 {clean_text}")
                            has_content = True
                else:
                    raw_text = message.content
                    clean_text = parser.parse(raw_text)
                    if clean_text.strip():
                        await msg.stream_token(f"🤖 {clean_text}")
                        has_content = True
            if has_content:
                await msg.send()
            if hasattr(message, "usage_metadata") and message.usage_metadata:
                usage = message.usage_metadata
                msg_tokens = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

                stream_tokens["input_tokens"] += msg_tokens["input_tokens"]
                stream_tokens["output_tokens"] += msg_tokens["output_tokens"]
                stream_tokens["total_tokens"] += msg_tokens["total_tokens"]
                if buffer:
                    stream_tokens.update({"buffer": clean_text})
                cl.user_session.set("usage_totals", stream_tokens)
                logger.debug(
                    "Input tokens: %d, Output tokens: %d, Total tokens: %d",
                    msg_tokens["input_tokens"],
                    msg_tokens["output_tokens"],
                    msg_tokens["total_tokens"],
                )
            await msg_thinking.remove()
            await msg_processing.remove()

    file_path = cl.user_session.get("file_path")
    file_name = cl.user_session.get("file_name")

    if file_path and file_name:
        await cl.Message(
            content="📄 Generated report is ready to download:",
            elements=[
                cl.File(
                    name=file_name,
                    path=file_path,
                    display="inline",
                )
            ],
        ).send()

    return stream_tokens


def get_single_mcp_client(server):
    mcp_config = mcp_servers_config[server].copy()
    mcp_config.pop("chainlit_command", None)
    mcp_client = MultiServerMCPClient({server: mcp_config})
    return mcp_client

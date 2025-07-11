from typing import List, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig

import chainlit as cl
from utils import generate_file_and_send, get_config, get_logger, strip_xml_tags

logger = get_logger(__name__)

config = get_config()

mcp_servers_config = config["mcp"]["servers"]
llm_agent_config = config["llm"]["agent"]


async def mcp_call(
    agent,
    messages: List[HumanMessage],
    thread_id: str,
    file_format: Optional[str] = None,
) -> Dict[str, int]:
    """Function to call mcp servers"""

    logger.info("Calling MCP servers for thread_id: %s", thread_id)

    stream_tokens = {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
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

    full_response_text = ""

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

            msg = cl.Message(content="")
            if message.tool_calls and isinstance(message.content, list):
                for chunk in message.content:
                    if (
                        isinstance(chunk, dict)
                        and chunk.get("type") == "text"
                        and chunk.get("text", "").strip()
                    ):
                        text = strip_xml_tags(chunk["text"])
                        full_response_text += text + "\n"
                        await msg.stream_token(f"🤖 {text}")
            else:
                text = strip_xml_tags(message.content)
                full_response_text += text + "\n"
                await msg.stream_token(f"🤖 {text}")

            await msg.send()
            if hasattr(message, "usage_metadata") and message.usage_metadata:
                usage = message.usage_metadata
                msg_tokens = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

                stream_tokens["total_input_tokens"] += msg_tokens["input_tokens"]
                stream_tokens["total_output_tokens"] += msg_tokens["output_tokens"]
                stream_tokens["total_tokens"] += msg_tokens["total_tokens"]

                logger.debug(
                    "Input tokens: %d, Output tokens: %d, Total tokens: %d",
                    msg_tokens["input_tokens"],
                    msg_tokens["output_tokens"],
                    msg_tokens["total_tokens"],
                )
            await msg_thinking.remove()
            await msg_processing.remove()
            if file_format and full_response_text.strip():
                await generate_file_and_send(full_response_text, file_format, msg.id)
    return {
        "input_tokens": stream_tokens["total_input_tokens"],
        "output_tokens": stream_tokens["total_output_tokens"],
        "total_tokens": stream_tokens["total_tokens"],
    }

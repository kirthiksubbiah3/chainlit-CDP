"""
Agent invocation helper.

Streams agent responses, handles tool output, file artifacts,
token usage tracking, and optional visualization rendering.
"""

from typing import List, Dict

import chainlit as cl
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
import matplotlib.pyplot as plt

from config import app_config
from utils import get_logger
from utils.text import CleanXMLTagParser


logger = get_logger(__name__)
llm_agent_config = app_config.llm_agent_config


async def invoke_agent(
    agent,
    messages: List[HumanMessage],
    thread_id: str,
    buffer: bool = False,
) -> Dict[str, int]:
    """
    Asynchronously invokes the provided agent with the given messages and thread ID.
    Processes the agent's response and returns token usage statistics.
    """

    logger.info("Calling MCP servers for thread_id: %s", thread_id)

    stream_tokens = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
    if "slack" in cl.user_session.get("user").identifier:
        is_slack = True
    else:
        is_slack = False

    if not is_slack:
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
        if not is_slack:
            await msg_processing.send()
        if "agent" in chunk:
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
                if not is_slack:
                    await msg_thinking.remove()
                    await msg_processing.remove()

        elif "tools" in chunk:
            for tool_msg in chunk["tools"]["messages"]:
                if (
                    (not isinstance(tool_msg, ToolMessage))
                    or (tool_msg.name not in ["get_file_contents"])
                    or (not tool_msg.artifact)
                ):
                    continue
                msg_tool = cl.Message(content=tool_msg.content)
                for art in tool_msg.artifact:
                    has_content = False
                    resource = getattr(art, "resource", None)
                    if not resource:
                        continue
                    text = getattr(resource, "text", None)
                    if text and text.strip():
                        clean_text = parser.parse(text.strip())
                        has_content = True
                        await msg_tool.stream_token(clean_text)
                    if has_content:
                        await msg_tool.send()

    file_path = cl.user_session.get("file_path")
    file_name = cl.user_session.get("file_name")

    x_axis = cl.user_session.get("x_axis")
    y_axis = cl.user_session.get("y_axis")
    operation = cl.user_session.get("operation")

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

    if x_axis and y_axis:
        logger.info("x_axis extracted:", x_axis )
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(x_axis, y_axis, marker="o", linestyle="-")
        elements = [cl.Pyplot(name="plot", figure=fig, display="inline")]
        await cl.Message(
            content=f"Simple graph with respect to {operation}",
            elements=elements,
        ).send()

    return stream_tokens

"""
Microsoft Teams bot integration for Atlassian MCP agent.

Handles incoming Teams messages, routes them to the MCP-powered
LangGraph agent, and returns responses to the user.
"""

from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.schema import Activity, ActivityTypes
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, AIMessage

from utils import get_logger
from config import app_config
from .mcp_client import get_mcp_client


logger = get_logger(__name__)

MICROSOFT_APP_ID = app_config.MICROSOFT_APP_ID
MICROSOFT_APP_PASSWORD = app_config.MICROSOFT_APP_PASSWORD
MICROSOFT_APP_TENANT_ID = app_config.MICROSOFT_APP_TENANT_ID
helpdesk_prompt_text = app_config.get_helpdesk_prompt()

settings = BotFrameworkAdapterSettings(
    app_id=MICROSOFT_APP_ID,
    app_password=MICROSOFT_APP_PASSWORD,
    channel_auth_tenant=MICROSOFT_APP_TENANT_ID,
    oauth_endpoint=f"https://login.microsoftonline.com/{MICROSOFT_APP_TENANT_ID}/v2.0",
)

adapter = BotFrameworkAdapter(settings)


async def run_agent_and_get_answer(
    messages,
    thread_id: str,
    user_id: str,
):
    logger.info(
        "Running agent for thread_id:%s user_id:%s",
        thread_id,
        user_id,
    )

    if isinstance(messages, str):
        messages = [HumanMessage(content=messages)]

    try:
        mcp_client = await get_mcp_client()
        combined_content = f"""
            {helpdesk_prompt_text}
            User Question: {messages}
            """
        final_messages = [HumanMessage(content=combined_content)]
        logger.info([type(m).__name__ for m in final_messages])

        _agent = mcp_client.agent
        final_answer = ""

        async for event in _agent.astream(
            {"messages": final_messages},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for node_data in event.values():
                if not isinstance(node_data, dict):
                    continue
                msgs = node_data.get("messages", [])
                for msg in msgs:
                    if not isinstance(msg, AIMessage):
                        continue
                    content = getattr(msg, "content", "")
                    if isinstance(content, str):
                        final_answer += content
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                final_answer += block.get("text", "")
                            elif isinstance(block, str):
                                final_answer += block

        return final_answer.strip() or "⚠️ No response from agent."

    except Exception as e:
        logger.error("Exception: %s", e) 
        return "⚠️ Something went wrong while running the agent."


async def on_turn(turn_context: TurnContext):
    """Handle a single Teams message turn."""
    if turn_context.activity.type != ActivityTypes.message:
        return

    incoming = turn_context.activity.text or ""
    if not incoming.strip():
        return

    # ---- Extract IDs (Teams equivalents) ----
    thread_id = turn_context.activity.conversation.id
    user_id = turn_context.activity.from_property.id
    channel_id = turn_context.activity.channel_id  # usually "msteams"
    safe_thread_id = thread_id.replace(":", "_")
    logger.info(
        "thread:%s user:%s channel_id:%s",
        safe_thread_id,
        user_id,
        channel_id,
    )

    try:
        agent_reply = await run_agent_and_get_answer(
            messages=incoming,
            thread_id=safe_thread_id,
            user_id=user_id,
        )

        await turn_context.send_activity(
            agent_reply or "⚠️ I couldn’t find a clear answer."
        )

    except Exception as e:
        logger.error("Agent error:", e)
        await turn_context.send_activity(
            "⚠️ Something went wrong while processing your request."
        )


async def process_teams_message(request):
    """Process an incoming Teams webhook request."""
    body = await request.json()
    auth_header = request.headers.get("Authorization", "")
    activity = Activity().deserialize(body)

    async def aux_func(turn_context):
        await on_turn(turn_context)

    try:
        await adapter.process_activity(activity, auth_header, aux_func)
        return JSONResponse(content={"status": "success"}, status_code=200)
    except Exception as e:
        logger.error("Agent error: %s", e)
        return JSONResponse(
            content={
                "error": "An internal error occurred while processing the bot activity."
            },
            status_code=500,
        )

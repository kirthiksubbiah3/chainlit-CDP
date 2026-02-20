from functools import lru_cache
from logging import getLogger

from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.schema import Activity, ActivityTypes
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, SystemMessage
import chainlit as cl

logger = getLogger(__name__)

@lru_cache()
def get_adapter() -> BotFrameworkAdapter:
    """
    Lazily create and cache the BotFrameworkAdapter.
    Prevents circular imports and avoids recreating adapter per request.
    """
    from config import app_config  # Lazy import prevents circular dependency

    settings = BotFrameworkAdapterSettings(
        app_id=app_config.MICROSOFT_APP_ID,
        app_password=app_config.MICROSOFT_APP_PASSWORD,
        channel_auth_tenant=app_config.MICROSOFT_APP_TENANT_ID,
        oauth_endpoint=f"https://login.microsoftonline.com/"
                       f"{app_config.MICROSOFT_APP_TENANT_ID}/v2.0",
    )

    return BotFrameworkAdapter(settings)


def get_helpdesk_prompt() -> str:
    """
    Lazy-load helpdesk prompt from config.
    """
    from config import app_config
    return app_config.get_helpdesk_prompt()



async def run_agent_and_get_answer(
    messages,
    thread_id: str,
    user_id: str,
):
    """
    Unified input for MCP agent.
    Works for Slack and Teams.
    """
    logger.info(f"Running agent for thread_id:{thread_id}, user_id:{user_id}")

    if isinstance(messages, str):
        messages = [HumanMessage(content=messages)]

    try:
        access_prompt = get_helpdesk_prompt()
        final_messages = [SystemMessage(content=access_prompt)] + messages

        logger.info([type(m).__name__ for m in final_messages])

        final_answer = ""

        async for event in _agent.astream(
            {"messages": final_messages},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for msg in event["model"]["messages"]:
                try:
                    final_answer += msg.content
                except Exception as exc:
                    logger.error(
                        f"Error processing model message {msg}: {exc}",
                        exc_info=True,
                    )
                    continue

        return final_answer.strip()

    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        return "⚠️ Something went wrong while running the agent."


# --------------------------------------------------
# Teams Turn Handler
# --------------------------------------------------

async def on_turn(turn_context: TurnContext):
    if turn_context.activity.type != ActivityTypes.message:
        return

    incoming = turn_context.activity.text or ""
    if not incoming.strip():
        return

    thread_id = turn_context.activity.conversation.id
    user_id = turn_context.activity.from_property.id
    channel_id = turn_context.activity.channel_id  # usually "msteams"

    safe_thread_id = thread_id.replace(":", "_")

    logger.info(
        f"thread:{safe_thread_id}, user:{user_id}, channel:{channel_id}"
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
        logger.error(f"Turn processing error: {e}", exc_info=True)
        await turn_context.send_activity(
            "⚠️ Something went wrong while processing your request."
        )


# --------------------------------------------------
# FastAPI Endpoint
# --------------------------------------------------

async def process_teams_message(request):
    """
    FastAPI route handler for Microsoft Teams messages.
    """
    adapter = get_adapter()  # Singleton adapter

    body = await request.json()
    auth_header = request.headers.get("Authorization", "")
    activity = Activity().deserialize(body)

    try:
        await adapter.process_activity(activity, auth_header, on_turn)
        return JSONResponse(content={"status": "success"}, status_code=200)

    except Exception as e:
        logger.error(f"Bot processing error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)
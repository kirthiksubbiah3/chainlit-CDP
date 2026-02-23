"""Token usage and cost calculation utilities"""

import chainlit as cl

from .get_log import get_logger

logger = get_logger(__name__)


def get_usage_cost_details(usage_totals: dict, input_token_cost, output_token_cost):
    """Returns token usage and cost details as a dict"""
    input_tokens = usage_totals.get("input_tokens", 0)
    output_tokens = usage_totals.get("output_tokens", 0)
    total_tokens = usage_totals.get("total_tokens", 0)

    input_cost = (input_tokens / 1000) * input_token_cost
    output_cost = (output_tokens / 1000) * output_token_cost
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def send_usage_cost_message(usage_totals: dict, input_token_cost, output_token_cost):
    """Sends token usage and cost details"""
    details = get_usage_cost_details(usage_totals, input_token_cost, output_token_cost)
    msg = (
        "📦 Token usage and approximate cost for this session. "
        f"The cost is calculated with ${input_token_cost} per 1000 input token and "
        f"${output_token_cost} per 1000 output token. Refer LLM Models official documentation "
        "for updated pricing.\n"
        f"- Total Input tokens: {details['input_tokens']}\n"
        f"- Total Output tokens: {details['output_tokens']}\n"
        f"- Total tokens: {details['total_tokens']}\n"
        f"- Input cost: ${details['input_cost']:.6f}\n"
        f"- Output cost: ${details['output_cost']:.6f}\n"
        f"- Total cost: ${details['total_cost']:.6f}"
    )
    return msg


def log_usage_details(usage_totals: dict, input_token_cost, output_token_cost, user):
    """Logs usage statistics and cost"""
    details = get_usage_cost_details(usage_totals, input_token_cost, output_token_cost)
    user_id = user.id if user else "unknown"
    logger.debug(
        "Total Input tokens: %d, Total Output tokens: %d, Total tokens: %d, "
        "Input cost: %.4f, Output cost: %.4f, Total cost: %.4f",
        details["input_tokens"],
        details["output_tokens"],
        details["total_tokens"],
        details["input_cost"],
        details["output_cost"],
        details["total_cost"],
    )
    logger.info("Logged in user: %s | Cost: $%.6f", user_id, details["total_cost"])


async def log_and_show_usage_details(
    profiles, usage_totals, chat_profile=None, env: str = "dev"
):
    """
    Log token usage details and optionally display cost information to the user.
    """
    if not chat_profile:
        chat_profile = cl.user_session.get("chat_profile")
    input_token_cost = profiles[chat_profile]["cost"]["input_token_cost"]
    output_token_cost = profiles[chat_profile]["cost"]["output_token_cost"]

    logger.info("input token cost is %s", input_token_cost)
    logger.info("output token cost is %s", output_token_cost)

    if "slack" not in cl.user_session.get("user").identifier and env == "dev":
        await cl.Message(
            content=send_usage_cost_message(
                usage_totals,
                input_token_cost,
                output_token_cost,
            )
        ).send()

    user = cl.user_session.get("user")
    log_usage_details(usage_totals, input_token_cost, output_token_cost, user)

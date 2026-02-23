"""Utility to generate a short chat title from conversation input using an LLM."""

async def generate_chat_title_from_input(llm, conversation: str) -> tuple:
    """
    Generate a short, descriptive chat title from a conversation using an LLM.

    Args:
        llm: Language model instance with an invoke method.
        conversation (str): Conversation text to summarize.

    Returns:
        tuple: (generated_title, usage_metadata)
    """
    
    title_prompt = (
        f"Create a short, descriptive title (3–5 words) without special characters and quotes "
        f"summarizing this conversation: {conversation}. Title:"
    )
    response = llm.invoke(title_prompt)
    title = response.content if hasattr(response, "content") else "New Chat"
    return title, response.usage_metadata

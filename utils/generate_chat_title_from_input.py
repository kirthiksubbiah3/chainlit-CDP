async def generate_chat_title_from_input(llm, conversation: str) -> tuple:
    title_prompt = (
        f"Create a short, descriptive title (3–5 words) without special characters and quotes "
        f"summarizing this conversation: {conversation}. Title:"
    )
    response = llm.invoke(title_prompt)
    title = response.content if hasattr(response, "content") else "New Chat"
    return title, response.usage_metadata

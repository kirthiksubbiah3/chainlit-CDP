"""Text processing and cleaning utilities"""

import re
from langchain_core.output_parsers import BaseOutputParser


class CleanXMLTagParser(BaseOutputParser[str]):
    """Parser to clean only <thinking> tags from LLM output."""

    def parse(self, text: str) -> str:
        # Remove <thinking>, </thinking>, or <thinking ...> tags
        if isinstance(text, list):
            text = " ".join(str(t) for t in text)
        elif not isinstance(text, str):
            text = " ".join(str(t) for t in text)
        elif not isinstance(text, str):
            text = str(text)
        return re.sub(r"</?thinking[^>]*>", "", text).strip()


def get_collection_name(suffix=None, name="chat_history") -> str:
    """Generate chromadb collection name. Expected a name containing 3-512 characters from
    [a-zA-Z0-9._-], starting and ending with a character in [a-zA-Z0-9]"""
    full_name = f"{name}_{suffix}" if suffix else name
    # Keep only allowed characters, replace others with "_"
    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", full_name)
    # Strip invalid characters from start/end
    safe_name = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", safe_name)
    # Ensure length limits
    safe_name = safe_name[:512].ljust(3, "_")
    return safe_name

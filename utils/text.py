"""Text processing and cleaning utilities"""

import re
from langchain_core.output_parsers import BaseOutputParser


class CleanXMLTagParser(BaseOutputParser[str]):
    """Parser to clean only <thinking> tags from LLM output."""

    def parse(self, text: str) -> str:
        # Remove <thinking>, </thinking>, or <thinking ...> tags
        return re.sub(r"</?thinking[^>]*>", "", text).strip()

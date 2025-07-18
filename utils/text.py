"""Text processing and cleaning utilities"""

import re
from langchain_core.output_parsers import BaseOutputParser


class CleanXMLTagParser(BaseOutputParser[str]):
    """Custom parser to clean XML-like tags from LLM output."""

    def parse(self, text: str) -> str:
        # Remove tags like <tag>...</tag> or <tag/>
        return re.sub(r"<[^>]+>", "", text).strip()

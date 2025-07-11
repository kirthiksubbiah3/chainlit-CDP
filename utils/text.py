"""Text processing and cleaning utilities"""

import re


def strip_xml_tags(text: str) -> str:
    """Removes XML-style tags from a string but keeps inner content."""
    return re.sub(r"<[^>]+>", "", text)


def clean_line(line: str) -> str:
    """Helper function to clean a line of text"""
    line = line.strip()
    line = re.sub(r"^#+\s*", "", line)
    line = re.sub(r"^\*\*\s*", "", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = line.replace("*", "")
    return line.strip()

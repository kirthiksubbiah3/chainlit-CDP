# file: attachment_reader.py

from typing import Optional
import os
import mimetypes

from langchain.tools import tool

from docx import Document as DocxDocument
from langchain_community.document_loaders import PyPDFLoader

# Config
MAX_INPUT_CHARS = 5000  # truncate long files


@tool
def read_attachment(filepath: str, max_chars: int = MAX_INPUT_CHARS) -> Optional[str]:
    """
    Use this tool when the user wants to summarize or ask query based on an attachment.
    Read any attachment (.txt, .docx, .pdf) and return plain text.
    Returns None if the file type is unsupported or file does not exist.
    """
    if not os.path.exists(filepath):
        return None

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".txt" and is_text_file(filepath):
            text = read_txt_file(filepath)
        elif ext == ".docx":
            text = read_docx_file(filepath)
        elif ext == ".pdf":
            text = read_pdf_file(filepath)
        else:
            return None
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return None

    # Truncate if too long
    text = text[:max_chars]
    return text


def is_text_file(filepath: str) -> bool:
    """Check if file is a plain text file using MIME type."""
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type is not None and mime_type.startswith("text")


def read_txt_file(filepath: str) -> str:
    """Read a text file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def read_docx_file(filepath: str) -> str:
    """Read a docx file and return plain text."""
    doc = DocxDocument(filepath)
    return "\n".join([para.text for para in doc.paragraphs])


def read_pdf_file(filepath: str) -> str:
    """Read a PDF file and return plain text."""
    loader = PyPDFLoader(filepath)
    docs = loader.load_and_split()
    return " ".join([doc.page_content for doc in docs])

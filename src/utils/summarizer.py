# file: attachment_reader.py

from typing import Optional
import os
import mimetypes

from docx import Document as DocxDocument
from langchain_community.document_loaders import PyPDFLoader

# Config
MAX_INPUT_CHARS = 5000  # truncate long files


def is_text_file(file_path: str) -> bool:
    """Check if file is a plain text file using MIME type."""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type is not None and mime_type.startswith("text")


def read_txt_file(file_path: str) -> str:
    """Read a text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def read_docx_file(file_path: str) -> str:
    """Read a docx file and return plain text."""
    doc = DocxDocument(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def read_pdf_file(file_path: str) -> str:
    """Read a PDF file and return plain text."""
    loader = PyPDFLoader(file_path)
    docs = loader.load_and_split()
    return " ".join([doc.page_content for doc in docs])


def read_attachment(file_path: str, max_chars: int = MAX_INPUT_CHARS) -> Optional[str]:
    """
    Read any supported attachment (.txt, .docx, .pdf) and return plain text.
    Returns None if the file type is unsupported or file does not exist.
    """
    if not os.path.exists(file_path):
        return None

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".txt" and is_text_file(file_path):
            text = read_txt_file(file_path)
        elif ext == ".docx":
            text = read_docx_file(file_path)
        elif ext == ".pdf":
            text = read_pdf_file(file_path)
        else:
            return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

    # Truncate if too long
    text = text[:max_chars]
    return text

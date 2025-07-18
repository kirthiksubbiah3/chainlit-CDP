from langchain.tools import tool
from docx import Document
import tempfile
import chainlit as cl


@tool
def generate_docx(content: str, filename: str) -> str:
    """
    Use this tool when the user wants the report in a Word document or DOCX file format.
    or want to save the output as a DOC file.
    the filename should be relevant to the content.
    """
    doc = Document()
    doc.add_paragraph(content)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(temp_file.name)

    cl.user_session.set("file_path", temp_file.name)
    cl.user_session.set("file_name", f"{filename}.docx")
    return temp_file.name

import chainlit as cl
import markdown2
from langchain.tools import tool
import tempfile
from weasyprint import HTML


@tool
def generate_pdf(content: str, filename: str) -> str:
    """
    Use this tool when the user wants to generate a PDF report or save the output as a PDF file.
    The content should be in markdown format.
    And the filename should be relevant to the content.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    # Convert Markdown content to HTML
    html_content = markdown2.markdown(content, extras=["fenced-code-blocks", "tables"])

    # Convert HTML to PDF
    HTML(string=html_content).write_pdf(temp_file.name)

    cl.user_session.set("file_path", temp_file.name)
    cl.user_session.set("file_name", f"{filename}")
    return temp_file.name

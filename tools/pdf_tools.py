from langchain.tools import tool
from fpdf import FPDF
import tempfile
import chainlit as cl


@tool
def generate_pdf(content: str, filename: str) -> str:
    """
    Use this tool when the user wants to generate a PDF report or save the output as a PDF file.
    the filename should be relevant to the content.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)

    cl.user_session.set("file_path", temp_file.name)
    cl.user_session.set("file_name", f"{filename}.pdf")
    return temp_file.name

import os
import chainlit as cl
import mermaid as md
from langchain.tools import tool


@tool
async def generate_mermaid_diagram(content: str, filename:str) -> str:
    """
    Use this tool when the user wants to generate a Mermaid graph image from chart or pipeline and
    show the image in the chat. The content should be the Mermaid syntax for the diagram.
    And the filename should be relevant to the content without any special character or extension.
    """
    render = md.Mermaid(content, width=800, height=600)
    output_dir = "mermaid"
    os.makedirs(output_dir, exist_ok=True)
    img_path = f"{output_dir}/{filename}.png"
    render.to_png(img_path)

    image_elt = cl.Image(path=img_path, name=filename, display="inline")
    # Attach the image to the message
    await cl.Message(
        content="Temporary image – save if needed!",
        elements=[image_elt],
    ).send()
    return img_path

import chainlit as cl

from utils import get_logger

logger = get_logger(__name__)


async def update_sidebar(rag_filenames):
    cl.user_session.set("rag_filenames", rag_filenames)
    logger.info("RAG filenames set in user session")
    props = {"filenames": rag_filenames}
    elements = [
        cl.CustomElement(
            name="DocumentListComponent",
            props=props,
        ),
    ]
    logger.info("Setting sidebar elements")
    await cl.ElementSidebar.set_elements(elements)
    await cl.ElementSidebar.set_title("RAG pdf files")

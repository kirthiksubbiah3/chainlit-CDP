"""
This is the main entry point for the application.
It imports the hooks module and the utils module
"""
 
from fastapi import Request

from chainlit.server import app
import chainlit as cl
 
from config import app_config
import hooks
from utils import get_logger
from utils.rag_file_manager import RagFileManager
 
logger = get_logger(__name__)

logger.info("Starting the app...")
logger.info("Imported module: %s", hooks.__name__)
logger.info("Loaded config from %s", app_config)
config = cl.config.load_config()
if not hasattr(config.features, "audio") or config.features.audio is None:
    config.features.audio = type("AudioConfig", (), {})()
config.features.audio.enabled = True
config.features.audio.sample_rate = 24000

rag_manager = RagFileManager()


@app.post("/rag/update")
async def update_rag(request: Request):
    """
    Webhook endpoint for Confluence 'Send web request'.
    Calls incremental RAG update directly (no subprocess).
    The expected JSON payload from Confluence should look like this:
    {
        "page_id": "{{page.id}}",
        "page_title": "{{page.title}}",
        "space_id":"{{space.id}}",
        "page_url": "{{page.url}}",
        "space_url": "{{space.url}}",
        "page_content": {{page.body}}
    }
    """
    data = await request.json()
    page_id = data["page_id"]
    page_title = data["page_title"]
    page_url = data["page_url"]
    space_id = data["space_id"]

    logger.info(f"Webhook received for pageId={page_id}, title={page_title}")
    if page_id in app_config.HELPDESK_CONFLUENCE_PAGE_IDS:
        try:
            content = data["page_content"]["content"][0]["content"][0]["text"]
            rag_manager.upsert_confluence_page(
                page_id=page_id,
                title=page_title,
                content=content,
                url=page_url,
                space_id=space_id
            )
            response = {"status": "success"}
        except Exception as e:
            logger.error(f"RAG update failed: {e}")
            response = {"status": "error", "detail": str(e)}
    else:
        logger.warning(
            f"Webhook received for unknown pageId={page_id},"
            f"title={page_title}")
        response = {"status": "invalid", "detail": "Unknown page updated"}
    return response
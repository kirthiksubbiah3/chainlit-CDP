#!/usr/bin/env python3
# scripts/confluence_chroma.py

"""
Build or incrementally update embeddings for Confluence pages in ChromaDB.
"""

import os
import json
import logging
import hashlib
from dotenv import load_dotenv
# from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("confluence_chroma")

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

CHROMA_PATH = os.getenv("CHROMADB_PERSISTENT_PATH", ".chromadb")
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "confluence_pages.json")
CACHE_HASH_FILE = os.path.join(os.path.dirname(__file__), "..", ".cache", "confluence_snapshot.json")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
COLLECTION_NAME = "confluence_rag_collection"

os.makedirs(os.path.dirname(CACHE_HASH_FILE), exist_ok=True)


def compute_hash(text: str) -> str:
    """Generate a short hash for detecting content changes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cached_snapshot() -> dict:
    if os.path.exists(CACHE_HASH_FILE):
        with open(CACHE_HASH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_snapshot(snapshot: dict):
    with open(CACHE_HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)


def incremental_embedding():
    """Embed only new or changed Confluence pages."""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError("Run confluence_fetch.py first to get page data.")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        pages = json.load(f)

    prev_snapshot = load_cached_snapshot()
    new_snapshot = {}

    to_embed = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for page in pages:
        key = f"{page['space']}::{page['title']}"
        text_hash = compute_hash(page["content"] + str(page["version"]))
        new_snapshot[key] = text_hash

        if key not in prev_snapshot or prev_snapshot[key] != text_hash:
            logger.info("Detected change in: %s", key)
            chunks = splitter.create_documents([page["content"]])
            for chunk in chunks:
                to_embed.append(Document(
                    page_content=chunk.page_content,
                    metadata={"space": page["space"], "title": page["title"]}
                ))

    if not to_embed:
        logger.info("No new or modified pages found. Skipping embedding.")
        return

    logger.info("Embedding %d new/updated documents...", len(to_embed))

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", region_name=AWS_REGION)
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
    )

    vectorstore.add_documents(to_embed)
    try:
        vectorstore.persist()
    except Exception:
        pass

    save_snapshot(new_snapshot)
    logger.info("Embedding complete and snapshot updated.")


if __name__ == "__main__":
    incremental_embedding()
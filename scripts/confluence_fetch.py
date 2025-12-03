#!/usr/bin/env python3
# scripts/confluence_fetch.py

"""
Fetch all Confluence pages across spaces and save them for embedding.
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("confluence_fetch")

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ATLASSIAN_EMAIL = os.getenv("CONFLUENCE_USERNAME")
ATLASSIAN_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")
CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL", "").rstrip("/")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_FILE = os.path.join(DATA_DIR, "confluence_pages.json")


def get_all_spaces(limit: int = 100) -> List[str]:
    """Fetch all available Confluence space keys."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/space"
    params = {"limit": limit}
    resp = requests.get(url, params=params, auth=(ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN))
    resp.raise_for_status()
    return [s["key"] for s in resp.json().get("results", [])]


def fetch_pages_from_space(space_key: str, limit: int = 100) -> List[Dict]:
    """Fetch all pages for a given space with last modified info."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content"
    pages = []
    start = 0

    while True:
        params = {
            "spaceKey": space_key,
            "limit": limit,
            "start": start,
            "expand": "body.storage,version"
        }
        resp = requests.get(url, params=params, auth=(ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN))
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])

        if not results:
            break

        for page in results:
            title = page.get("title", "Untitled")
            version = page.get("version", {}).get("number", 1)
            modified = page.get("version", {}).get("when", "")
            html = page.get("body", {}).get("storage", {}).get("value", "")
            text = BeautifulSoup(html, "html.parser").get_text(separator="\n").strip()

            page_id = page.get("id", "")
            url_path = page.get("_links", {}).get("webui", "")
            page_url = f"{CONFLUENCE_BASE_URL}{url_path}" if url_path else "Unknown"

            pages.append({
                "id": page_id,
                "space": space_key,
                "title": title,
                "version": version,
                "last_modified": modified,
                "url": page_url,
                "content": text or "Empty page"
            })

        start += len(results)
        if len(results) < limit:
            break

    return pages


def fetch_all_confluence_pages() -> List[Dict]:
    """Fetch all spaces and all pages."""
    os.makedirs(DATA_DIR, exist_ok=True)
    all_pages = []
    spaces = get_all_spaces()
    logger.info("Found %d spaces: %s", len(spaces), spaces)

    for space in spaces:
        logger.info("Fetching space: %s", space)
        pages = fetch_pages_from_space(space)
        all_pages.extend(pages)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d pages to %s", len(all_pages), CACHE_FILE)
    return all_pages


if __name__ == "__main__":
    fetch_all_confluence_pages()

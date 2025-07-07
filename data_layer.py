"""data layer for chainlit chat history persistence"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import os
import logging

from chromadb import PersistentClient
import chainlit as cl
import chainlit.data as cl_data
from chainlit.types import (
    Feedback,
    ThreadDict,
    Pagination,
    PageInfo,
    PaginatedResponse,
    ThreadFilter,
)
from chainlit.element import Element, ElementDict
from chainlit.step import StepDict


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(
    "📁 ChromaDB instance is running in: %s",
    os.path.abspath(".chromadb"),
)


def utc_now_str():
    """return current utc time"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def doc_id(thread_id: str, step_id: str):
    """return thread and step id"""
    return f"{thread_id}_{step_id}"


class CustomDataLayer(cl_data.BaseDataLayer):
    """class for custom data layer"""

    def __init__(self):
        self.chroma_client = PersistentClient(path=".chromadb")
        self.collection = self.chroma_client.get_or_create_collection(
            name="chat_history"
        )

    async def get_user(self, identifier: str) -> Optional[cl.PersistedUser]:
        logger.info("User logged in: %s", identifier)
        return cl.PersistedUser(
            id=identifier, createdAt=utc_now_str(), identifier=identifier
        )

    async def create_user(self, user: cl.User) -> Optional[cl.PersistedUser]:
        logger.info("Creating user in db: %s", user.identifier)

        return cl.PersistedUser(
            id=user.identifier,
            createdAt=utc_now_str(),
            identifier=user.identifier,
        )

    async def delete_feedback(self, feedback_id: str) -> bool:
        return True

    async def upsert_feedback(self, feedback: Feedback) -> str:
        return ""

    async def create_element(self, element: "Element"):
        pass  # Not used

    async def get_element(
        self, thread_id: str, element_id: str
    ) -> Optional["ElementDict"]:
        return None  # Not used

    async def delete_element(self, element_id: str, thread_id: Optional[str] = None):
        pass  # Not used

    async def create_step(self, step_dict: "StepDict"):
        if (
            step_dict["output"]
            == "🤖 Hello, welcome to Sentinel Mind! How can I help you?"
        ):
            return

        logger.info(
            "Creating step_id %s for  thread_id %s",
            step_dict["id"],
            step_dict["threadId"],
        )
        metadata = {
            "thread_id": step_dict["threadId"],
            "step_id": step_dict["id"],
            "type": step_dict["type"],
            "name": step_dict["name"],
            "createdAt": step_dict["createdAt"],
            "user_id": cl.user_session.get("user").identifier,
        }

        self.collection.add(
            ids=[doc_id(step_dict["threadId"], step_dict["id"])],
            documents=[step_dict["output"]],
            metadatas=[metadata],
        )

    async def update_step(self, step_dict: "StepDict"):
        logger.info(
            "Updating step_id %s for thread_id %s",
            step_dict["id"],
            step_dict["threadId"],
        )
        # Just delete and re-add the step for simplicity
        await self.delete_step(step_dict["id"])
        await self.create_step(step_dict)

    async def delete_step(self, step_id: str):
        all_data = self.collection.get()
        for i, meta in enumerate(all_data["metadatas"]):
            if meta["step_id"] == step_id:
                self.collection.delete(ids=[all_data["ids"][i]])
                break

    async def get_thread_author(self, thread_id: str) -> str:
        results = self.collection.get(where={"thread_id": thread_id})
        if results["metadatas"]:
            return results["metadatas"][0].get("user_id", "unknown")
        return "unknown"

    async def delete_thread(self, thread_id: str):
        logger.info("Deleting thread: %s", thread_id)
        all_data = self.collection.get()
        ids_to_delete = []

        for i, meta in enumerate(all_data["metadatas"]):
            if meta.get("thread_id") == thread_id:
                ids_to_delete.append(all_data["ids"][i])

        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)

    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse[ThreadDict]:
        all_data = self.collection.get()
        thread_map = {}

        # keys: ids embeddings documents uris included data metadatas
        for meta in all_data["metadatas"]:
            thread_id = meta["thread_id"]

            if filters.userId and meta.get("user_id") != filters.userId:
                continue
            if thread_id not in thread_map:
                thread_map[thread_id] = {
                    "id": thread_id,
                    "name": f"Thread {thread_id[:6]}",
                    "userId": meta["user_id"],
                    "userIdentifier": meta["user_id"],
                    "createdAt": meta["createdAt"],
                    "steps": [],
                }

        return PaginatedResponse(
            data=list(thread_map.values()),
            pageInfo=PageInfo(
                hasNextPage=False,
                startCursor=None,
                endCursor=None,
            ),
        )

    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        results = self.collection.get(where={"thread_id": thread_id})
        if not results["metadatas"]:
            return None

        steps = [
            {
                "id": meta["step_id"],
                "name": meta["name"],
                "type": meta["type"],
                "createdAt": meta["createdAt"],
                "output": doc,
            }
            for doc, meta in zip(results["documents"], results["metadatas"])
        ]
        steps.sort(key=lambda x: x["createdAt"])
        return {
            "id": thread_id,
            "name": f"Thread {thread_id[:6]}",
            "createdAt": steps[0]["createdAt"] if steps else utc_now_str(),
            "userId": results["metadatas"][0]["user_id"],
            "userIdentifier": results["metadatas"][0]["user_id"],
            "steps": steps,
        }

    # pylint: disable=too-many-arguments
    # pylint: disable=R0917
    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        logger.info("Updating thread %s", thread_id)

    async def build_debug_url(self) -> str:
        return ""

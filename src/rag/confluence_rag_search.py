"""
Confluence RAG search module.

Provides semantic search over Confluence documents stored in ChromaDB
using Bedrock embeddings.
"""

import os
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from utils import get_logger

logger = get_logger(__name__)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


class ConfluenceRagManager:
    """Manager to handle RAG operations for Confluence documents stored in ChromaDB"""

    def __init__(self):
        self.embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1",
            region_name=AWS_REGION,
        )

    async def query(
        self,
        question: str,
        k: int = 3,
        collection_name: str = "confluence_rag_collection",
    ):
        """
        Query the Confluence vector store for semantically similar chunks.
        """
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=os.getenv("CHROMADB_PERSISTENT_PATH", ".chromadb"),
        )

        results = vectorstore.similarity_search(question, k=k)
        for i, res in enumerate(results, 1):
            logger.debug(
                "Result %d: %s... (source: %s)",
                i,
                res.page_content[:120],
                res.metadata.get("source"),
            )

        return results

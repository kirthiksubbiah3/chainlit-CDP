import os
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from utils import get_logger


logger = get_logger(__name__)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


class S3RagManager:
    """Manager to handle RAG operations for GitHub README files stored in S3"""

    def __init__(self):
        self.embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name=AWS_REGION
        )

    async def query(self, question, k=3, collection_name="s3_rag_collection"):
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=os.getenv("CHROMADB_PERSISTENT_PATH", ".chromadb"),
        )

        results = vectorstore.similarity_search(question, k=k)
        for i, res in enumerate(results, 1):
            logger.debug("Result %s: %s...", i, res.page_content[:100])

        return results

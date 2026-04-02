import os

from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from utils import get_logger
from data_layer import ChromaDataLayer

logger = get_logger(__name__)


class RagFileManager(ChromaDataLayer):
    """
    RAG manager supporting:
    - Azure OpenAI embeddings
    - Chroma vectorstore
    - Upsertion of Confluence page content
    - Semantic query
    """

    def __init__(self, collection_name: str = "confluence_rag_collection"):
        super().__init__()

        logger.info(f"Initializing vectorstore: {collection_name}")

        self.embeddings = AzureOpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-01")
        )

        self.vectorstore = Chroma(
            collection_name=collection_name,
            client=self.chroma_client,
            embedding_function=self.embeddings,
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    def upsert_confluence_page(self, page_id: str, title: str, content: str, url: str, space_id: str):
        """
        Clean, chunk, embed, and upsert a single Confluence page into Chroma.
        Deletes old chunks first. Idempotent.
        """

        logger.info(f"Upserting Confluence page: {page_id} | {title}")

        # STEP 1: Delete old vectors
        self.vectorstore.delete(where={"page_id": page_id})

        # STEP 2: Chunk page content
        chunks = self.splitter.split_text(content)
        logger.info(f"Chunked into {len(chunks)} segments")

        # STEP 3: Build LangChain docs
        docs = []
        for idx, chunk in enumerate(chunks):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "page_id": page_id,
                        "title": title,
                        "space_id": space_id,
                        "url": url,
                        "chunk_index": idx,
                    }
                )
            )

        # STEP 4: Insert into vectorstore
        if docs:
            self.vectorstore.add_documents(docs)
            logger.info(f"Stored {len(docs)} chunks for page_id={page_id}")
        else:
            logger.warning(f"No content to insert for page_id={page_id}")

    async def query(self, question: str, k: int = 3):
        logger.info(f"Querying vectorstore for: {question}")
        results = self.vectorstore.similarity_search(question, k=k)
        return results
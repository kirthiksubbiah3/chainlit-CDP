"""
RAG file manager.

Handles user-uploaded files, extracts text content,
embeds it using Bedrock, and stores vectors in ChromaDB.
"""
from typing import List

import chainlit as cl
from PyPDF2 import PdfReader
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitte

from data_layer import ChromaDataLayer
from utils import get_logger
from utils.text import get_collection_name

logger = get_logger(__name__)


class RagFileManager(ChromaDataLayer):
    """Manages ingestion and lifecycle of RAG documents stored in ChromaDB."""

    def __init__(self, collection_name=None):
        super().__init__()
        if not collection_name:
            if cl.user_session:
                collection_name = get_collection_name(
                    cl.user_session.get("user").identifier, name="rag_files"
                )
            else:
                collection_name = "rag_files"
        logger.debug("Initializing Bedrock embeddings model")
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name="us-east-1"
        )
        self.vectorstore = Chroma(
            collection_name=collection_name,
            client=self.chroma_client,
            embedding_function=embeddings,
        )

    async def upload_and_store_file(self, filepath: str, filename: str):
        """Extract text from a file and store it in the vector database."""

        logger.info("Starting upload and store process for file: %s", filepath)
        text = ""

        # Extract text from PDF file
        try:
            logger.debug("Attempting to read PDF file: %s", filepath)
            reader = PdfReader(filepath)
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text
            logger.info(
                "Extracted text from file: %s (length: %d characters)",
                filepath,
                len(text),
            )
        except Exception as exc:
            logger.error(
                "Failed to read or extract text from PDF: %s. Error: %s",
                filepath,
                exc,
            )
            return

        # Return early if no text was extracted
        if not text.strip():
            logger.warning(
                "No text extracted from file: %s. Skipping processing.",
                filepath,
            )
            return

        # Split text into chunks for better processing
        logger.debug("Splitting extracted text into chunks")
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.create_documents([text])
        logger.info("Text split into %d chunks", len(chunks))

        # Create Document objects with metadata for vector storage
        docs = [
            Document(
                page_content=chunk.page_content,
                metadata={"filepath": filepath, "filename": filename},
            )
            for chunk in chunks
        ]
        logger.debug(
            "Created %d Document objects for vector store ingestion",
            len(docs),
        )
        # Add documents to vector store
        logger.debug("Adding documents to vector store")
        self.vectorstore.add_documents(docs)

        logger.info("Completed upload and store for file: %s", filepath)

    async def get_all_documents(self) -> List:
        """Return a sorted list of filenames stored in the vector database."""

        all_docs = self.vectorstore.get(include=["metadatas"])

        filenames = {
            metadata["filename"]
            for metadata in all_docs["metadatas"]
            if "filename" in metadata
        }
        return sorted(filenames)

    async def delete_file(self, filename):
        """Delete all vector entries associated with a filename."""
        self.vectorstore.delete(where={"filename": filename})

# rag_file_manager.py

import chainlit as cl
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from PyPDF2 import PdfReader
from typing import List
from utils import get_logger
from utils.text import get_collection_name
from data_layer import ChromaDataLayer

logger = get_logger(__name__)


class RagFileManager(ChromaDataLayer):
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
            embedding_function=embeddings
        )

    async def upload_and_store_file(self, filepath: str, filename: str):
        logger.info(f"Starting upload and store process for file: {filepath}")
        text = ""

        # Extract text from PDF file
        try:
            logger.debug(f"Attempting to read PDF file: {filepath}")
            reader = PdfReader(filepath)
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text
            logger.info(
                f"Extracted text from file: {filepath} (length: {len(text)} characters)"
            )
        except Exception as e:
            logger.error(
                f"Failed to read or extract text from PDF: {filepath}. Error: {e}"
            )
            return

        # Return early if no text was extracted
        if not text.strip():
            logger.warning(
                f"No text extracted from file: {filepath}. Skipping processing."
            )
            return

        # Split text into chunks for better processing
        logger.debug("Splitting extracted text into chunks")
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.create_documents([text])
        logger.info(f"Text split into {len(chunks)} chunks")

        # Create Document objects with metadata for vector storage
        docs = [
            Document(
                page_content=chunk.page_content,
                metadata={"filepath": filepath, "filename": filename},
            )
            for chunk in chunks
        ]
        logger.debug(f"Created {len(docs)} Document objects for vector store ingestion")
        # Add documents to vector store
        logger.debug("Adding documents to vector store")
        self.vectorstore.add_documents(docs)

        logger.info(f"Completed upload and store for file: {filepath}")

    async def get_all_documents(self) -> List:
        all_docs = self.vectorstore.get(include=["metadatas"])

        filenames = {
            metadata["filename"]
            for metadata in all_docs["metadatas"]
            if "filename" in metadata
        }
        return sorted(filenames)

    async def delete_file(self, filename):
        self.vectorstore.delete(where={"filename": filename})

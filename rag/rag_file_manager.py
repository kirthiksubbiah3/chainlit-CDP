# rag_file_manager.py

from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from PyPDF2 import PdfReader
from typing import List

from utils import get_logger

logger = get_logger(__name__)


class RagFileManager:
    def __init__(self, chroma_path=".chromadb", collection_name="rag_files"):
        self.chroma_path = chroma_path
        self.collection_name = collection_name

    async def upload_and_store_file(self, file_path: str):
        logger.info(f"Starting upload and store process for file: {file_path}")
        text = ""

        # Extract text from PDF file
        try:
            logger.debug(f"Attempting to read PDF file: {file_path}")
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text
            logger.info(
                f"Extracted text from file: {file_path} (length: {len(text)} characters)"
            )
        except Exception as e:
            logger.error(
                f"Failed to read or extract text from PDF: {file_path}. Error: {e}"
            )
            return

        # Return early if no text was extracted
        if not text.strip():
            logger.warning(
                f"No text extracted from file: {file_path}. Skipping processing."
            )
            return

        # Split text into chunks for better processing
        logger.debug("Splitting extracted text into chunks")
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.create_documents([text])
        logger.info(f"Text split into {len(chunks)} chunks")

        # Create Document objects with metadata for vector storage
        docs = [
            Document(page_content=chunk.page_content, metadata={"source": file_path})
            for chunk in chunks
        ]
        logger.debug(f"Created {len(docs)} Document objects for vector store ingestion")

        # Initialize AWS Bedrock embeddings model
        logger.debug("Initializing Bedrock embeddings model")
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name="us-east-1"
        )

        # Create or load Chroma vector store
        logger.debug("Creating/loading Chroma vector store")
        vectorstore = Chroma(
            persist_directory=self.chroma_path,
            collection_name=self.collection_name,
            embedding_function=embeddings,
        )

        # Add documents to vector store
        logger.debug("Adding documents to vector store")
        vectorstore.add_documents(docs)

        # Persist changes to disk
        logger.info(f"Persisting vector store to: {self.chroma_path}")
        vectorstore.persist()
        logger.info(f"Completed upload and store for file: {file_path}")

    async def get_all_documents(self) -> List[str]:
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name="us-east-1"
        )
        vectorstore = Chroma(
            persist_directory=self.chroma_path,
            collection_name=self.collection_name,
            embedding_function=embeddings,
        )

        all_docs = vectorstore.get(include=["metadatas"])
        sources = {
            metadata["source"]
            for metadata in all_docs["metadatas"]
            if "source" in metadata
        }
        return sorted(sources)

    def getVectorStore(self) -> Chroma:
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name="us-east-1"
        )
        try:
            vectorstore = Chroma(
                persist_directory=self.chroma_path,
                collection_name=self.collection_name,
                embedding_function=embeddings,
            )
            logger.info("Vectorstore loaded")
        except Exception:
            vectorstore = Chroma.from_documents(
                [],
                embedding=embeddings,
                collection_name=self.collection_name,
                persist_directory=self.chroma_path,
            )
            logger.info("Vectorstore created")
        return vectorstore

    async def delete_file(self, file_name):
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name="us-east-1"
        )
        try:
            vectorstore = Chroma(
                persist_directory=self.chroma_path,
                collection_name=self.collection_name,
                embedding_function=embeddings,
            )
        except Exception:
            vectorstore = Chroma.from_documents(
                [],
                embedding=embeddings,
                collection_name=self.collection_name,
                persist_directory=self.chroma_path,
            )
        vectorstore.delete(where={"source": file_name})

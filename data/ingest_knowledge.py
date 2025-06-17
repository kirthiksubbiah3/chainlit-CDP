# %%
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_aws import BedrockEmbeddings

# Load environment variables from .env file in the project root
load_dotenv()

# --- Configuration using absolute paths for robustness ---
# Get the directory of the current script (data/)
SCRIPT_DIR = Path(__file__).resolve().parent
# Get the project root directory (one level up from data/)
PROJECT_ROOT = SCRIPT_DIR.parent

KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "knowledge_base.pdf"
CHROMA_DB_DIRECTORY = PROJECT_ROOT / "chroma_db"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def build_vector_store():
    """
    Builds a persistent vector store from a PDF knowledge base.
    This script is location-aware and saves the DB to the project root.
    """
    print("--- Starting Knowledge Base Ingestion ---")

    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"❌ Error: Knowledge base file not found at '{KNOWLEDGE_BASE_PATH}'")
        return

    if CHROMA_DB_DIRECTORY.exists():
        print(f"🧹 Found existing database. Deleting '{CHROMA_DB_DIRECTORY}' to rebuild.")
        shutil.rmtree(CHROMA_DB_DIRECTORY)

    print(f"📚 Loading documents from '{KNOWLEDGE_BASE_PATH}'...")
    loader = PyMuPDFLoader(str(KNOWLEDGE_BASE_PATH))
    documents = loader.load()
    if not documents:
        print("❌ Error: No documents were loaded from the PDF. Is it empty?")
        return
    print(f"✅ Loaded {len(documents)} pages/documents.")

    print("🧠 Initializing Bedrock embeddings model...")
    embeddings = BedrockEmbeddings(
        region_name=AWS_REGION,
        model_id="amazon.titan-embed-text-v1"
    )
    print("✅ Embeddings model initialized.")

    print(f"💾 Creating and persisting vector store at '{CHROMA_DB_DIRECTORY}'...")
    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(CHROMA_DB_DIRECTORY)
    )
    print(f"✅ Vector store created successfully with {len(documents)} documents.")
    print("--- Ingestion Complete ---")


if __name__ == "__main__":
    # To run this script, navigate to the data folder in your terminal
    # and execute `python ingest_knowledge.py`, or run it from your IDE.
    build_vector_store()

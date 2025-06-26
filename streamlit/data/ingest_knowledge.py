# %%
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_aws import BedrockEmbeddings
from tqdm import tqdm

# Load environment variables from .env file in the project root
load_dotenv()

# --- Configuration using absolute paths for robustness ---
# Get the directory of the current script (data/)
SCRIPT_DIR = Path(__file__).resolve().parent
# Get the project root directory (one level up from data/)
PROJECT_ROOT = SCRIPT_DIR.parent

KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data"
CHROMA_DB_DIRECTORY = PROJECT_ROOT / "chroma_db"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def build_vector_store():
    """
    Builds a persistent vector store from a PDF knowledge base.
    This script is location-aware and saves the DB to the project root.
    """
    print("--- Starting Knowledge Base Ingestion ---")

    # 1. Check if the source directory exists
    if not KNOWLEDGE_BASE_PATH.is_dir():
        print(
            f"❌ Error: Source PDF directory not found at "
            f"'{KNOWLEDGE_BASE_PATH}'"
        )
        return

    # 2. Find all PDF files in the source directory
    print(f"📚 Scanning for PDF files in '{KNOWLEDGE_BASE_PATH}'...")
    pdf_files = list(KNOWLEDGE_BASE_PATH.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ Error: No PDF files found in '{KNOWLEDGE_BASE_PATH}'.")
        return

    print(f"✅ Found {len(pdf_files)} PDF file(s) to process.")

    # 3. Load all documents from all PDF files
    all_documents = []
    print(
        "📖 Loading documents from each PDF file "
        "(each page becomes a document)..."
    )
    for pdf_path in tqdm(pdf_files, desc="Loading PDFs"):
        try:
            loader = PyMuPDFLoader(str(pdf_path))
            documents_from_file = loader.load()
            all_documents.extend(documents_from_file)
            tqdm.write(
                f"  -> Loaded {len(documents_from_file)} pages from "
                f"'{pdf_path.name}'"
            )
        except Exception as e:  # pylint: disable=W0718
            tqdm.write(
                f"  -> ⚠️  Warning: Could not load '{pdf_path.name}'. "
                f"Skipping. Error: {e}"
            )

    if not all_documents:
        print(
            "❌ Error: No documents could be loaded from any of the PDF "
            "files.\n"
            "   Are they empty or corrupt?"
        )
        return

    print(
        f"\n✅ Total of {len(all_documents)} pages/documents loaded "
        "from all files."
    )

    # 4. Clean up existing database if it exists
    # (break long comment into multiple lines to fit within 79 characters)
    if CHROMA_DB_DIRECTORY.exists():
        print(
            f"🧹 Found existing database. Deleting "
            f"'{CHROMA_DB_DIRECTORY}' to rebuild."
        )
        shutil.rmtree(CHROMA_DB_DIRECTORY)

    # 5. Initialize Bedrock embeddings
    print("🧠 Initializing Bedrock embeddings model...")
    embeddings = BedrockEmbeddings(
        region_name=AWS_REGION,
        model_id=(
            "amazon.titan-embed-text-v1"
        )
    )
    print("✅ Embeddings model initialized.")

    # 6. Create and persist the vector store using the combined documents
    print(
        f"💾 Creating and persisting vector store at "
        f"'{CHROMA_DB_DIRECTORY}'..."
    )
    Chroma.from_documents(
        documents=all_documents,  # Use the combined list of documents from all
        # PDFs
        embedding=embeddings,
        persist_directory=str(CHROMA_DB_DIRECTORY)
    )
    print(
        f"✅ Vector store created successfully with "
        f"{len(all_documents)} documents."
    )
    print("--- Ingestion Complete ---")


if __name__ == "__main__":
    # To run this script, navigate to the data folder in your terminal
    # and execute `python ingest_knowledge.py`, or run it from your IDE.
    build_vector_store()

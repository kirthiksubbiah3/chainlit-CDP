# %%
import os
import shutil
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_aws import BedrockEmbeddings
from tqdm import tqdm

# Load environment variables from .env file in the project root
load_dotenv()

# --- Configuration using absolute paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Use new PDF source folder for structured reports
PDF_SOURCE_DIR = PROJECT_ROOT / "data" / "page_reports"
CHROMA_DB_DIRECTORY = PROJECT_ROOT / "chroma_db"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def split_tasks_by_marker(text: str, source_name: str):
    """
    Splits raw PDF text into a list of LangChain Document objects based on the '# Task:' marker.
    """
    sections = re.split(r"(?=# Task:)", text)
    documents = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        documents.append(Document(
            page_content=section,
            metadata={"source": f"{source_name} [Task {i+1}]"}
        ))

    return documents


def build_vector_store():
    """
    Builds a persistent vector store from structured PDF reports.
    Each '# Task:' block is treated as an individual document.
    """
    print("--- Starting Knowledge Base Ingestion ---")

    if not PDF_SOURCE_DIR.is_dir():
        print(f"❌ Error: PDF source folder not found: {PDF_SOURCE_DIR}")
        return

    pdf_files = list(PDF_SOURCE_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in '{PDF_SOURCE_DIR}'.")
        return

    print(f"✅ Found {len(pdf_files)} PDF file(s) in '{PDF_SOURCE_DIR}'")

    all_documents = []

    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        try:
            loader = PyMuPDFLoader(str(pdf_path))
            pages = loader.load()
            full_text = "\n\n".join([p.page_content for p in pages])
            task_docs = split_tasks_by_marker(full_text, pdf_path.name)

            all_documents.extend(task_docs)
            tqdm.write(f"  -> Extracted {len(task_docs)} tasks from '{pdf_path.name}'")

        except Exception as e:
            tqdm.write(f"  ⚠️ Skipped '{pdf_path.name}' — Error: {e}")

    if not all_documents:
        print("❌ No tasks were extracted. Aborting.")
        return

    print(f"\n✅ Total of {len(all_documents)} task documents prepared.")

    # Clean old DB
    if CHROMA_DB_DIRECTORY.exists():
        print(f"🧹 Deleting existing vector store at '{CHROMA_DB_DIRECTORY}'...")
        shutil.rmtree(CHROMA_DB_DIRECTORY)

    # Embed and persist
    print("🧠 Initializing Bedrock embeddings...")
    embeddings = BedrockEmbeddings(
        region_name=AWS_REGION,
        model_id=(
            "amazon.titan-embed-text-v1"
        )
    )

    print(f"💾 Saving vector store to '{CHROMA_DB_DIRECTORY}'...")
    Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        persist_directory=str(CHROMA_DB_DIRECTORY)
    )

    print(f"✅ Ingested {len(all_documents)} task documents into vector DB.")
    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    build_vector_store()

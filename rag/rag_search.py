# rag_tool.py
from langchain_core.tools import tool
from .rag_file_manager import RagFileManager


@tool
def rag_search(query: str) -> str:
    """Answer questions based on uploaded documents using RAG."""
    rag_manager = RagFileManager()
    results = rag_manager.vectorstore.similarity_search(query, k=4)
    formatted = "\n\n---\n\n".join([doc.page_content for doc in results])
    return formatted

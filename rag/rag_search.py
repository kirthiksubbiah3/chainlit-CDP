# rag_tool.py
from langchain_core.tools import tool
from .rag_file_manager import RagFileManager

rag_manager = RagFileManager(chroma_path=".chromadb", collection_name="rag_files")


@tool
def rag_search(query: str) -> str:
    """Answer questions based on uploaded documents using RAG."""
    vectorstore = rag_manager.getVectorStore()
    results = vectorstore.similarity_search(query, k=4)
    formatted = "\n\n---\n\n".join([doc.page_content for doc in results])
    return formatted

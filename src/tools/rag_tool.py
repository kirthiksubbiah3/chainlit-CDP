from langchain_core.tools import tool
from utils.rag_file_manager import RagFileManager

@tool
def rag_search(query: str, page_id: str) -> str:
    """Answer questions based on uploaded documents using RAG for a specific Confluence page."""
    rag_manager = RagFileManager()
    results = rag_manager.vectorstore.similarity_search(
        f"{query} with page_id {page_id}", k=4
    )
    return "\n\n---\n\n".join([doc.page_content for doc in results])
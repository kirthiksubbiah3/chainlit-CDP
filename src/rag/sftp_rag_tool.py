"""
S3/SFTP RAG tool.

Provides a LangChain tool for performing semantic search over
repository or SFTP-backed documents using RAG.
"""

from langchain_core.tools import tool

from rag.sftp_rag_search import S3RagManager


@tool
async def readme_rag_search(query: str) -> str:
    """
    Perform a semantic search from files using readme_rag_search (Retrieval-Augmented Generation).
    **When to use this tool:**
    - When the user asks a question about how a GitHub repository works,
      such as “Install Grafana with Helm on GKE?”, “How to install it?”, or
      “What dependencies are required?”
    - compulsory include the (source: <filename>) also to the UI for users reference.
    - When you need contextual or technical information **that already exists in the stored files**.
    - When you want the model to give accurate, repository-specific answers instead of guessing.

    Example usage:
        >>> response = await readme_rag_search("Install Grafana with Helm on GKE?")
        >>> print(response)

    This will return the most relevant parts of the files that describe deployment steps.
    """
    manager = S3RagManager()
    results = await manager.query(question=query, k=3)
    formatted = "\n\n---\n\n".join([doc.page_content for doc in results])
    return formatted

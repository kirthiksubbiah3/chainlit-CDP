# confluence_rag_tool.py
from langchain_core.tools import tool
from rag.confluence_rag_search import ConfluenceRagManager


@tool
async def confluence_rag_search(query: str) -> str:
    """
    Perform a semantic search on Confluence documentation using RAG.

    **When to use this tool:**
    - When the user asks questions related to Confluence project documentation.
    - When you need to fetch context or explanations from existing Confluence pages.
    - Always include the (source: <pagename>) in the UI so users can trace answers.
    - Use this to ensure responses are grounded in the latest Confluence data instead of guesses.

    Example:
        >>> response = await confluence_rag_search("How to configure deployment in Sentinel?")
        >>> print(response)

    This returns the most relevant Confluence content chunks for the question.
    """
    manager = ConfluenceRagManager()
    results = await manager.query(question=query, k=3)

    formatted = "\n\n---\n\n".join(
        [
            f"{doc.page_content}\n(source: {doc.metadata.get('source', 'Unknown')})"
            for doc in results
        ]
    )

    return formatted

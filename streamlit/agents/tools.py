# %%
import asyncio
import os
import warnings
import json

from pathlib import Path
from dotenv import load_dotenv
from browser_use import Agent as BrowserUseAgent
from langchain_community.vectorstores import Chroma
from langchain_aws import BedrockEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from models.bedrock import Bedrock

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Load environment variables
load_dotenv()

# --- Configuration ---
anthem_username = os.getenv("anthem_username")
anthem_password = os.getenv("anthem_password")
login_url = os.getenv("ANTHEM_LOGIN_URL")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Define project root
CHROMA_DB_DIRECTORY = PROJECT_ROOT / "chroma_db"  # Use absolute path

# %% --- Bedrock and Vector Store Initialization ---
model_tool = Bedrock().get_model_details()
embeddings = BedrockEmbeddings(
    region_name=AWS_REGION,
    model_id=(
        "amazon.titan-embed-text-v1"
    )
)
vector_store = Chroma(
    persist_directory=str(CHROMA_DB_DIRECTORY),
    embedding_function=embeddings
)


# THIS IS THE CRITICAL FIX: A simpler, more reliable retriever.
retriever = vector_store.as_retriever(search_kwargs={"k": 1})

# --- Tool Definitions ---


def get_instructions(user_query: str) -> str:
    """
    Retrieves and VALIDATES the most relevant task instructions from the
    knowledge base.
    1. Retrieves the top document from ChromaDB.
    2. Uses an LLM to validate if the retrieved doc is relevant to the user's
       query.
    3. If relevant, formats and returns the instructions.
    4. If not relevant, returns a status indicating no instructions were found.
    """
    print(
        f"TOOL (Stage 1 - Retrieval): Searching knowledge base for query: "
        f"'{user_query}'"
    )
    docs = retriever.invoke(user_query)

    if not docs:
        print(
            "TOOL (Stage 1 - Retrieval): No documents found in vector store."
        )
        return "STATUS: NO_INSTRUCTIONS_FOUND"

    retrieved_text = docs[0].page_content
    print("TOOL (Stage 1 - Retrieval): Found a candidate document.")

    # --- Stage 2: LLM Validation Gate ---
    print("TOOL (Stage 2 - Validation): Asking LLM to validate relevance.")
    validation_prompt = ChatPromptTemplate.from_template(
        """
        You are a strict relevance validation expert.
        Your task is to determine if the RETRIEVED_DOCUMENT provides
        the necessary steps to complete the USER_QUERY.

        USER_QUERY: "{query}"

        RETRIEVED_DOCUMENT:
        ---
        {document}
        ---

        Does the RETRIEVED_DOCUMENT contain a direct plan to address the
        USER_QUERY?
        Answer with only the word 'yes' or 'no'.
        """
    )
    validation_chain = validation_prompt | model_tool | StrOutputParser()
    response = validation_chain.invoke({
        "query": user_query,
        "document": retrieved_text
    })
    # Clean up the response to be robust
    is_relevant = response.strip().lower() == 'yes'
    print(f"""TOOL (Stage 2 - Validation): LLM validation result:
          '{response.strip()}' -> Is Relevant: {is_relevant}""")

    if not is_relevant:
        print(
            "TOOL (Stage 3 - Decision): Document is NOT relevant. Discarding."
        )
        return "STATUS: NO_INSTRUCTIONS_FOUND"

    # --- Stage 3: Formatting and Output ---
    print(
        "TOOL (Stage 3 - Decision): Document IS relevant. "
        "Formatting instructions."
    )

    # Substitute placeholders with actual credentials
    final_instructions = retrieved_text.replace(
        "{{ANTHEM_USERNAME}}", anthem_username
    )
    final_instructions = final_instructions.replace(
        "{{ANTHEM_PASSWORD}}", anthem_password
    )
    final_instructions = final_instructions.replace(
        "{{ANTHEM_LOGIN_URL}}", login_url
    )

    # Return a structured JSON string.
    # This is more robust than parsing plain text.
    result = {
        "status": "SUCCESS",
        "instructions": final_instructions
    }
    return json.dumps(result)


# %%
def run_browser_task(task: str) -> str:
    """
    Uses the browser-use Agent to execute a task. The task can be either
    detailed instructions from the KB or the original user query.
    """
    async def _inner():
        agent = BrowserUseAgent(
            task=(
                f"You will be given a set of instructions. "
                f"First, navigate to the login page at {login_url}. "
                f"Use these credentials to login: "
                f"username '{anthem_username}', "
                f"password '{anthem_password}'. "
                f"Then, execute the following plan precisely:\n\n"
                f"{task}"
            ),
            llm=model_tool,
            use_vision=True,
            max_failures=5,
        )
        history = await agent.run()
        if history.extracted_content():
            return str(history.extracted_content()[-1])
        return "Task completed successfully."

    return asyncio.run(_inner())

import os
import logging
import boto3
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_chroma import Chroma

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS and S3 configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Chroma configuration
CHROMADB_PERSISTENT_PATH = os.getenv("CHROMADB_PERSISTENT_PATH", ".chromadb")

# Initialize S3 client
s3 = boto3.client("s3", region_name=AWS_REGION)


class S3EmbeddingBuilder:
    """Fetch README files from S3 and store embeddings in Chroma"""

    def __init__(self, collection_name="s3_rag_collection"):
        logger.info("Initializing Bedrock embeddings model")
        self.collection_name = collection_name
        self.embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1", region_name=AWS_REGION
        )
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=CHROMADB_PERSISTENT_PATH
        )

    def load_readmes_from_s3(self):
        """List README files in the S3 bucket"""
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME)
        readme_files = [
            obj["Key"]
            for obj in response.get("Contents", [])
            if "README" in obj["Key"]
        ]
        return readme_files

    def build_and_save_embeddings(self):
        """Embed README content and store in Chroma"""
        documents = []
        readme_files = self.load_readmes_from_s3()

        if not readme_files:
            logger.warning("No README files found in S3 bucket.")
            return

        for key in readme_files:
            obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            text = obj["Body"].read().decode("utf-8")

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = splitter.create_documents([text])

            for chunk in chunks:
                # Store both filename and filepath in metadata
                documents.append(
                    Document(
                        page_content=chunk.page_content,
                        metadata={
                            "filename": key,
                            "filepath": key  # You can adjust if you want a full path
                        }
                    )
                )

        logger.info(
            "Adding %d documents to Chroma collection '%s'",
            len(documents),
            self.collection_name
        )
        self.vectorstore.add_documents(documents)
        logger.info("Embedding and storage complete.")


if __name__ == "__main__":
    builder = S3EmbeddingBuilder()
    builder.build_and_save_embeddings()

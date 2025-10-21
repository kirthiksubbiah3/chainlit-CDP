import base64
import logging
import os
import boto3
import requests
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# Configuration from env
GITHUB_API = os.getenv("GITHUB_API", "https://api.github.com")
OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
BRANCH = os.getenv("BRANCH", "heads/main")
TOKEN = os.getenv("GITHUB_TOKEN")

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Logging
logging.basicConfig(level=logging.INFO)

# GitHub headers
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Initialize S3 client
s3 = boto3.client("s3", region_name=AWS_REGION)


def get_repo_tree(owner, repo, branch):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()["tree"]


def fetch_readme_files(tree, owner, repo):
    readmes = []
    for item in tree:
        if item["path"].endswith("README.md") and item["type"] == "blob":
            file_url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{item['path']}"
            resp = requests.get(file_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            content = resp.json()["content"]
            decoded = base64.b64decode(content).decode("utf-8")
            readmes.append((item["path"], decoded))
    return readmes


def clear_s3_bucket(bucket):
    objects = s3.list_objects_v2(Bucket=bucket)
    if "Contents" in objects:
        for obj in objects["Contents"]:
            s3.delete_object(Bucket=bucket, Key=obj["Key"])


def upload_to_s3(bucket, files):
    for path, content in files:
        s3.put_object(Bucket=bucket, Key=path, Body=content.encode("utf-8"))


def main():
    tree = get_repo_tree(OWNER, REPO, BRANCH)
    readmes = fetch_readme_files(tree, OWNER, REPO)
    clear_s3_bucket(S3_BUCKET)
    upload_to_s3(S3_BUCKET, readmes)
    logging.info("Completed README sync to S3")


if __name__ == "__main__":
    main()

from langchain_core.tools import tool
import os
import httpx

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")


@tool("get_gitlab_projects")
async def get_gitlab_projects():
    """Fetch GitLab projects accessible to the user."""
    url = f"{GITLAB_URL}/api/v4/projects?membership=true&per_page=5"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    res.raise_for_status()
    projects = res.json()

    return [{"id": p["id"], "name": p["name"]} for p in projects]


@tool("get_gitlab_pipelines")
async def get_gitlab_pipelines(project_id: str):
    """Fetch pipelines for a given GitLab project."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipelines?per_page=5"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    res.raise_for_status()
    return res.json()


@tool("get_gitlab_jobs")
async def get_gitlab_jobs(project_id: str, pipeline_id: str):
    """Fetch jobs for a given pipeline in a GitLab project."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/pipelines/{pipeline_id}/jobs"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    res.raise_for_status()
    return res.json()


@tool("get_gitlab_job_logs")
async def get_gitlab_job_logs(project_id: str, job_id: str):
    """Fetch logs for a specific GitLab job."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/jobs/{job_id}/trace"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    res.raise_for_status()
    return res.text[-1000:]
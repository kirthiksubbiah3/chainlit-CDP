import json
import httpx
import requests
from typing import Dict, Any
from requests.auth import HTTPBasicAuth
from langchain_core.tools import tool
from config import app_config

ATLASSIAN_API_BASE = app_config.ATLASSIAN_API_BASE
ATLASSIAN_ACCESS_KEY = app_config.ATLASSIAN_ACCESS_KEY
ATLASSIAN_ORG_ID = app_config.ATLASSIAN_ORG_ID
ATLASSIAN_DIRECTORY_ID = app_config.ATLASSIAN_DIRECTORY_ID
ATLASSIAN_BASE_URL = app_config.ATLASSIAN_BASE_URL
ATLASSIAN_USERNAME = app_config.ATLASSIAN_USERNAME
ATLASSIAN_API_TOKEN = app_config.ATLASSIAN_API_TOKEN

@tool("get_atlassian_org_users_or_accounts")
async def get_atlassian_org_users_or_accounts() -> Dict[str, Any]:
    """
    Fetch role assignments for a user in Atlassian Admin.
    """
    if not all([ATLASSIAN_ORG_ID, ATLASSIAN_ACCESS_KEY]):
        raise ValueError(
            "Missing Atlassian API keys ATLASSIAN_ORG_ID and "
            "ATLASSIAN_ACCESS_KEY. Please check your .env file."
        )

    url = (
        f"{ATLASSIAN_API_BASE}/admin/v2/orgs/{ATLASSIAN_ORG_ID}/"
        f"directories/{ATLASSIAN_DIRECTORY_ID}/users"
    )
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ATLASSIAN_ACCESS_KEY}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        return {
            "error": "Failed to fetch users",
            "status_code": resp.status_code,
            "response": resp.text,
        }

    return resp.json()


@tool("get_atlassian_user_role_assignments")
async def get_atlassian_user_role_assignments(
    accountId: str,
) -> Dict[str, Any]:
    """
    Fetch role assignments for a user in Atlassian Admin.
    """

    url = (
        f"{ATLASSIAN_API_BASE}/admin/v2/orgs/{ATLASSIAN_ORG_ID}/"
        f"directories/{ATLASSIAN_DIRECTORY_ID}/users/{accountId}/role-assignments"
    )
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ATLASSIAN_ACCESS_KEY}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        return {
            "error": "Failed to fetch role assignments",
            "status_code": resp.status_code,
            "response": resp.text,
        }

    return resp.json()

@tool("create_jira_project")
async def create_jira_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new Jira project using the provided payload.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    auth = HTTPBasicAuth(ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN)
    data = json.dumps(payload)

    resp = requests.post(
        f"{ATLASSIAN_BASE_URL}/rest/api/3/project",
        headers=headers,
        auth=auth,
        data=data,
    )

    return resp.json()

@tool("create_confluence_space")
async def create_confluence_space(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new Confluence space using the provided payload.
    """
    url = f"{ATLASSIAN_BASE_URL}/wiki/api/v2/spaces"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={"Accept": "application/json"},
            auth=(ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN),
            json=payload, 
        )

    resp.raise_for_status()
    return resp.json()


@tool("get_jsm_project_portals")
async def get_jsm_project_portals() -> Dict[str, Any]:
    """
    Get Jira Service Management projects.
    """

    url = f"{ATLASSIAN_BASE_URL}/rest/servicedeskapi/servicedesk"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Accept": "application/json"},
            auth=(ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN),
        )

    resp.raise_for_status()
    return resp.json()


@tool("get_jsm_request_types")
async def get_jsm_request_types(service_desk_id: str) -> Dict[str, Any]:
    """
    Get Jira Service Management request types for a given project.
    """
    url = f"{ATLASSIAN_BASE_URL}/rest/servicedeskapi/servicedesk/{service_desk_id}/requesttype"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Accept": "application/json"},
            auth=(ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN),
        )

    resp.raise_for_status()
    return resp.json()


@tool("get_jsm_forms")
async def get_jsm_forms(
    service_desk_id: str, request_type_id: str
) -> Dict[str, Any]:
    """
    Get Jira Service Management forms for a given project and request type.
    """
    url = (
        f"{ATLASSIAN_BASE_URL}/rest/servicedeskapi/servicedesk/"
        f"{service_desk_id}/requesttype/{request_type_id}/field"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url,
            headers={"Accept": "application/json"},
            auth=(ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN),
        )

    resp.raise_for_status()
    return resp.json()

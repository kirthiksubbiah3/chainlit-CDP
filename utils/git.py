import re
import json
import os
from git import Repo, GitCommandError
import shutil

from pathlib import Path


BASE_PATH = Path(__file__).resolve().parents[2]

TEMPL_WORKSPACE = os.path.join(BASE_PATH, "tmp", "templates")
BASE_WORKSPACE = os.path.join(BASE_PATH, "tmp", "user_projects")

BOILER_PLATES = {
    "react": {
        "url": "https://github.com/react-boilerplate/react-boilerplate-cra-template.git"
    }
}

GIT_PATH = shutil.which("git")
# TODO Remove or add files as required. Make sure user has permission to add workflow
EXCLUDE = [".git", ".env", "__pycache__", ".DS_Store", "workflows"]

if GIT_PATH is None:
    raise RuntimeError("git executable not found in PATH")


def ignore_patterns(src, names):
    return [name for name in names if name in EXCLUDE]


def copy_items(src, dst):
    """
    Copy contents of src to dst
    """
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        if item in EXCLUDE:
            continue
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=ignore_patterns, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


async def clone_repo(
    repo_url: str,
    new_name: str,
    target_path: str = "",
    private: bool = False,
    replace: bool = False,
):
    """
    Clone the repo_url to a local target_path. If the url is of private repo, will add token
    """
    status, msg = True, ""
    if not target_path:
        if not new_name:
            new_name = repo_url.split("/")[-1].removesuffix(".git")
        target_path = os.path.join(BASE_WORKSPACE, new_name)

    if private:
        username = os.environ["GITHUB_USERNAME"]
        token = os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]
        repo_url = f"https://{username}:{token}@github.com/{username}/{repo_url.split('/')[-1]}"

    if (not os.path.exists(target_path)) or replace:
        try:
            os.makedirs(target_path, exist_ok=True)
            Repo.clone_from(repo_url, target_path)
        except GitCommandError as e:
            status, msg = False, f"Git error: {str(e)}"
    return {"status": status, "msg": msg, "path": target_path}


async def commit_and_push_code(repo_path: str, remote_url: str):
    """
    Commit items at local repo_path and push to remote_url
    """
    status, msg = True, ""
    try:
        repo = Repo(repo_path)
        username = os.environ["GITHUB_USERNAME"]
        token = os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]
        remote_url = f"https://{username}:{token}@github.com/{username}/{remote_url.split('/')[-1]}"
        repo.remote().set_url(remote_url)
        origin = repo.remote(name="origin")
        repo.git.add(all=True)
        repo.index.commit("Initial commit")
        repo.git.branch("-M", "main")
        origin.push(refspec="main", set_upstream=True)
    except GitCommandError as e:
        status, msg = False, f"Git error: {str(e)}"
    return {"status": status, "msg": msg, "path": repo_path}


async def create_repo_from_boilerplate(
    repo_name: str, repo_url: str, project_type: str
):
    """
    Clone a given project_type code and copy contents to new repo, then commit and push
    """
    status, msg, repo_path = True, "", ""
    boilerplate_url = BOILER_PLATES[project_type]["url"]
    try:
        bp_path = os.path.join(TEMPL_WORKSPACE, project_type)
        await clone_repo(boilerplate_url, repo_name, target_path=bp_path)
        result = await clone_repo(repo_url, repo_name, private=True)
        repo_path = result["path"]
        copy_items(bp_path, repo_path)
        await commit_and_push_code(repo_path, repo_url)
    except GitCommandError as e:
        status, msg = False, f"Git error: {str(e)}"
    return {"status": status, "msg": msg, "path": repo_path}


async def get_git_details_from_input(llm, conversation) -> tuple:
    """
    Call the llm to get the git url from the chat
    """
    title_prompt = (
        f'Analyse the conversation "{conversation}". Get the git repo name and url of the project. '
        f'Your response content should not contain any extra text or explanation.'
        f'Return only the repo name and git url in format "{{"repo_name": "", "repo_url": ""}}":'
    )
    response = llm.invoke(title_prompt)
    content = response.content if hasattr(response, "content") else "{}"
    cleaned = re.sub(r'^.*?(\{.*\}).*$', r'\1', content, flags=re.DOTALL)
    content = json.loads(cleaned)
    return content, response.usage_metadata

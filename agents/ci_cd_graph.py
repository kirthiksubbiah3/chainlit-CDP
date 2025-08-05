import re
import chainlit as cl

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from typing_extensions import TypedDict

from agents.react_agent import tools_mcp_server_agent
from utils.git import (
    create_repo_from_boilerplate,
    get_git_details_from_input,
    BOILER_PLATES,
)


# # --- State Model ---
class ProjectState(TypedDict, total=False):
    repo_url: str
    project_name: str
    description: str
    private: str
    content: str
    new_msg: str
    project_type: str
    buffer: str
    thread_id: str
    llm: str
    usage_totals: dict


async def extract_project_info(state: ProjectState) -> ProjectState:
    """Extract project type from the content of the state.
    This function checks the content of the state for keywords that match
    the predefined project types in BOILER_PLATES. If a match is found,
    it sets the project_type in the state. If no match is found, it prompts
    the user to enter a valid project type from the available options."""
    # old_state is what you saved from last run
    old_state = cl.user_session.get("graph_state", {})
    prompt = old_state.get("content", "") + f'. {state["new_msg"]}'
    state["content"] = prompt
    cl.user_session.set("graph_state", state)
    git_data, state["usage_totals"] = await get_git_details_from_input(state["llm"], prompt)
    project_name = git_data.get("repo_name", False)
    if not project_name:
        user_inp = await cl.AskUserMessage("Enter project name:").send()
        project_name = user_inp["output"].strip()
    state["project_name"] = project_name
    project_type = "not_valid"
    valid_projects = ".".join([f"\n--> {key}" for key in BOILER_PLATES])
    while project_type not in BOILER_PLATES:
        for key in BOILER_PLATES:
            if key in prompt.lower():
                project_type = key
                break
        if project_type != "not_valid":
            break
        else:
            user_inp = await cl.AskUserMessage(
                f"Enter valid project type: {valid_projects}"
            ).send()
            if not user_inp:
                break
            project_type = user_inp["output"].strip()
    state["content"] = re.sub(project_type, "", prompt, flags=re.IGNORECASE)
    state["project_type"] = project_type
    return state


async def get_project_info(state: ProjectState) -> ProjectState:
    state.update(
        {
            "description": "Custom project",
            "private": "private",
        }
    )
    return state


async def create_repo(state: ProjectState) -> ProjectState:
    message = (
        f' {state["content"]} .Create {state["private"]} repo named {state["project_name"]}'
        f' with description {state["description"]}. Return repo name and url:'
    )

    messages = [HumanMessage(content=message)]
    resp = await tools_mcp_server_agent(
        "github", messages, state["llm"], state["thread_id"], buffer=True
    )
    state["buffer"] = resp.pop("buffer")
    git_data, usage_metadata = await get_git_details_from_input(state["llm"], state["buffer"])
    repo_url = git_data["repo_url"]
    if not repo_url.endswith(".git"):
        repo_url = repo_url + ".git"
    state["repo_url"] = repo_url
    usage_totals = state["usage_totals"].copy()
    state["usage_totals"] = {k: resp[k] + usage_metadata[k] + usage_totals[k] for k in resp}
    return state


async def fetch_boilerplate(state: ProjectState) -> ProjectState:
    if state["project_type"]:
        await create_repo_from_boilerplate(
            state["project_name"], state["repo_url"], state["project_type"]
        )
    return state


# --- Build Graph ---
def make_graph():
    builder = StateGraph(ProjectState)

    builder.add_node("extract_project_info", extract_project_info)
    builder.add_node("get_info", get_project_info)
    builder.add_node("create_repo", create_repo)
    builder.add_node("fetch_boilerplate", fetch_boilerplate)

    builder.set_entry_point("extract_project_info")
    builder.add_edge("extract_project_info", "get_info")
    builder.add_edge("get_info", "create_repo")
    builder.add_edge("create_repo", "fetch_boilerplate")
    builder.add_edge("fetch_boilerplate", END)

    return builder.compile()


ci_cd_graph = make_graph()

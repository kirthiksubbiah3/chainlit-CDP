import chainlit as cl
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.serde import jsonplus
# from .fastapi_endpoint import sentinelmind_api_post

from . import (
    get_time_taken_message,
    get_logger,
    log_and_show_usage_details,
    generate_chat_title_from_input,
)

from .serializer import _custom_msgpack_default


jsonplus._msgpack_default = _custom_msgpack_default


# Load environment variables
load_dotenv()
logger = get_logger(__name__)
invoke_agent = get_llm = RagFileManager = update_sidebar = react_repo_agent = (
    default_agent
) = Observability = PodRestartAgent = MCPServerSession = SupervisorAgent = (
    CustomDataLayer
) = Cryptowallet = app_config = None


def _setup_agent_imports():
    global \
        react_repo_agent, \
        Observability, \
        PodRestartAgent, \
        SupervisorAgent, \
        Cryptowallet
    if (
        react_repo_agent is None
        or Observability is None
        or PodRestartAgent is None
        or SupervisorAgent is None
        or Cryptowallet is None
    ):
        from agents.react_repo_agent import (
            react_repo_agent as imported_react_repo_agent,
        )
        from agents.observability_agent import (
            Observability as imported_Observability,
        )
        from agents.cryptowallet_agent import (
            Cryptowallet as imported_Cryptowallet,
        )
        from agents.pod_restart_agent import (
            PodRestartAgent as imported_PodRestartAgent,
        )
        from agents.supervisor_agent import (
            SupervisorAgent as imported_SupervisorAgent,
        )

        react_repo_agent = imported_react_repo_agent
        Observability = imported_Observability
        PodRestartAgent = imported_PodRestartAgent
        SupervisorAgent = imported_SupervisorAgent
        Cryptowallet = imported_Cryptowallet


def _setup_imports():  # lazy import to avoid circular import
    global \
        invoke_agent, \
        get_llm, \
        RagFileManager, \
        update_sidebar, \
        default_agent, \
        MCPServerSession, \
        CustomDataLayer, \
        app_config
    if (
        invoke_agent is None
        or get_llm is None
        or RagFileManager is None
        or update_sidebar is None
        or default_agent is None
        or MCPServerSession is None
        or CustomDataLayer is None
        or app_config is None
    ):
        from invoke_agent import invoke_agent as imported_invoke_agent
        from llm import get_llm as imported_get_llm
        from rag.rag_file_manager import (
            RagFileManager as imported_RagFileManager,
        )
        from rag.update_sidebar import (
            update_sidebar as imported_update_sidebar,
        )
        from agents.default_agent import (
            default_agent as imported_default_agent,
        )
        from mcp_tools import MCPServerSession as imported_MCPServerSession
        from data_layer import CustomDataLayer as imported_CustomDataLayer
        from config import app_config as imported_app_config

        invoke_agent = imported_invoke_agent
        get_llm = imported_get_llm
        RagFileManager = imported_RagFileManager
        update_sidebar = imported_update_sidebar
        default_agent = imported_default_agent
        MCPServerSession = imported_MCPServerSession
        CustomDataLayer = imported_CustomDataLayer
        app_config = imported_app_config


async def fetch_chat_history_for_thread(thread_id: str) -> list:
    """
    Fetch chat history for a given thread ID from the CustomDataLayer.

    Args:
        thread_id: The thread ID to fetch history for

    Returns:
        List of HumanMessage objects representing the chat history messages for the thread
        where each message is converted from the document content string to HumanMessage format.
    """
    _setup_imports()
    cdl = CustomDataLayer()
    documents = await cdl.get_document(thread_id)

    # Extract human documents (every even index)
    human_docs = [doc for i, doc in enumerate(documents) if i % 2 == 0]
    human_msgs = [HumanMessage(content=doc) for doc in human_docs]

    logger.info(
        f"Retrieved {len(human_msgs)} chat history messages for thread {thread_id}"
    )
    return human_msgs


async def generate_response(
    msg: str,
    mcp_servers_config_to_pass: dict,
    mcp_service_config: dict,
    profiles: dict,
    starters: dict,
    env: str,
    filepath: str = "",
):
    _setup_imports()
    logger.info(f"Profiles is {profiles}")
    set_profiles_agent(profiles)

    start_time = time.perf_counter()
    thread_id = cl.context.session.thread_id

    user = cl.user_session.get("user")
    logger.info("User is %s", user.id)
    messages, usage_data_title = [], {}
    if filepath:
        summarize_file_prompt = SystemMessage(
            content=f"""
            If the user asks to summarize the uploaded file, pass {filepath}
            to the read_attachment tool to extract its content and
            provide a concise summary of their content.
        """
        )
        messages.append(summarize_file_prompt)
    # Add security-focused system message
    security_filter_prompt = SystemMessage(
        content="""
        Security Notice:

        You MUST NOT ask for or process any sensitive user information like:
        - Passwords
        - API keys
        - Access tokens
        - TLS certificates
        - Secrets
        - Anything resembling credentials or private configuration

        If a user provides such data (even accidentally), respond only with this message:
        "For your security, please do NOT share sensitive credentials or secrets. "
        "They have been ignored."

        Do not echo or use any such sensitive content in your response. Only proceed with
        safe content.
    """
    )
    messages.append(security_filter_prompt)
    # If msg has a .content attribute (Message object), use that
    # Otherwise, fall back to treating it as a string
    msg_text = getattr(msg, "content", msg)
    msg_command = getattr(msg, "command", None)
    logger.info(f"Message command is {msg_command} for {msg_text}")
    if msg_text:  # make sure it's not None
        msg_lower = msg_text.lower()
        # Additional guidance if login mentioned
        if "login" in msg_lower:
            service_msg = (
                f"Search the {mcp_service_config} to find the corresponding URL and "
                "credentials if required or not provided. "
                "Never share credentials in prompt or anywhere even if asked."
            )
            messages.append(SystemMessage(content=service_msg))

        # Human message from user
        messages.append(HumanMessage(content=msg_text))

        profiles_agent = cl.user_session.get("profiles_agent")
        session_type = "tools"
        # s msg_lower = msg.lower()
        if msg_command:
            logger.info("Command received: %s", msg_command)
            target_server = msg_command
            if msg_command in ["Browser", "Browser-HL", "Sentinel-Mind"]:
                session_type = "server"
                target_server = "playwright"
            elif msg_command == "supervisor":
                session_type = "supervisor"
            elif msg_command == "Observability":
                _setup_agent_imports()
                obs = Observability()
                session_type = "observability"
            elif msg_command == "cryptowallet":
                _setup_agent_imports()
                crypto = Cryptowallet()
                session_type = "cryptowallet"
            elif msg_command == "sflabs-docs":
                messages.append(
                    SystemMessage(
                        content="Always use readme_rag_search tool for this prompt."
                    )
                )
            elif msg_command == "Confluence":
                messages.append(
                    SystemMessage(
                        content=(
                            "Always use the confluence_rag_search tool for this query. "
                            "Do NOT use any other tools or sources. "
                            "Search strictly within the Confluence documentation embeddings "
                            "stored in the vector database. "
                            "Return only content found in those Confluence pages, "
                            "and include the source page name for reference."
                        )
                    )
                )
            elif msg_command == "Atlassian":
                access_prompt = app_config.get_helpdesk_prompt()
                messages.append(HumanMessage(content=access_prompt))
                messages.append(
                    SystemMessage(
                        content=(
                            "You are a atlassian assistant.\n"
                            "Default behavior:\n"
                            "- Respond ONLY with a concise natural-language summary.\n"
                            "- Do NOT output raw JSON, objects, arrays, or field names.\n"
                            "- Do NOT include explanations, steps, or metadata.\n"
                            "- Use bullet points only if necessary.\n\n"
                            "Only provide detailed or step-by-step information"
                            "IF the user explicitly asks "
                            "for details, explanation, or raw data."
                        )
                    )
                )
            messages.append(
                SystemMessage(
                    content=f"Forward this to {target_server} mcp server"
                )
            )
            logger.info(
                "Using %s session agent for %s command",
                session_type,
                msg_command,
            )

        chat_profile_name = cl.user_session.get("chat_profile")
        # Condition for Slack messages
        if (not chat_profile_name) and (
            "slack" in cl.user_session.get("user").identifier
        ):
            chat_profile_name = next(iter(profiles))
            cl.user_session.set("chat_profile", chat_profile_name)
            # TODO Added this session_type for slack messages. Change if required
            session_type = "tools"

        llm = get_llm(chat_profile_name)
        if session_type == "tools":
            #    if not msg_command == "agent's_api":
            usage_totals = await invoke_agent(
                profiles_agent, messages, thread_id
            )
        #    else:
        #         logger.info("Using sentinelmind_api_tool for agents_api command with endpoint as %s", app_config.sentinelmind_api_agent )
        #         promptmsg = msg.content
        #         json_payload = [ {"role": "user", "content": promptmsg} ]
        #         endpoint = f"{app_config.sentinelmind_base_url}/{app_config.sentinelmind_api_agent}/"
        #         apiresponse = sentinelmind_api_post(url=endpoint, json_data=json_payload)
        #         logger.info("SentinelMind API response: %s", apiresponse)

        #         logger.info("Response content: %s", apiresponse.get("content", "No content field in response"))
        #         await cl.Message(content=apiresponse.get("content", "No content field in response")).send()
        #         usage_totals = {"input_tokens": apiresponse.get("input_tokens", 0), "output_tokens": apiresponse.get("output_tokens", 0), "total_tokens": apiresponse.get("input_tokens", 0) + apiresponse.get("output_tokens", 0)}

        elif session_type == "observability":
            human_msgs = await fetch_chat_history_for_thread(thread_id)
            messages.extend(human_msgs)
            usage_totals = await obs.custom_graph_agent(
                messages, llm, thread_id
            )
        elif session_type == "cryptowallet":
            human_msgs = await fetch_chat_history_for_thread(thread_id)
            messages.extend(human_msgs)
            usage_totals = await crypto.custom_graph_agent(
                messages, llm, thread_id
            )
        elif session_type == "supervisor":
            human_msgs = await fetch_chat_history_for_thread(thread_id)
            messages.extend(human_msgs)
            usage_totals = await SupervisorAgent(llm).run(messages, thread_id)
        else:
            mcp_server_session = MCPServerSession(
                target_server, messages, llm, thread_id, buffer=False
            )
            usage_totals = await mcp_server_session.client_session_per_server()

        # Setting thread title
        thread_title = cl.user_session.get("thread_title")

        if not thread_title:
            if isinstance(msg_text, str) and len(msg_text.split()) > 2:
                (
                    thread_title,
                    usage_data_title,
                ) = await generate_chat_title_from_input(llm, msg)
                cl.user_session.set("thread_title", thread_title)

        if "slack" not in cl.user_session.get("user").identifier:
            response_time = get_time_taken_message(start_time)
            if env == "dev":
                await cl.Message(content=response_time).send()
            logger.info(response_time)

        if usage_data_title:
            usage_totals["input_tokens"] += usage_data_title["input_tokens"]
            usage_totals["output_tokens"] += usage_data_title["output_tokens"]
            usage_totals["total_tokens"] += usage_data_title["total_tokens"]

        await log_and_show_usage_details(
            profiles, usage_totals, chat_profile_name, env
        )


def set_profiles_agent(profiles: dict):
    chat_profile = cl.user_session.get("chat_profile")
    logger.info("Chat profile set in user session: %s", chat_profile)
    user = cl.user_session.get("user")
    if (
        (not chat_profile)
        and user is not None
        and ("slack" in getattr(user, "identifier", ""))
    ):
        chat_profile = next(iter(profiles))
    if not chat_profile or chat_profile not in profiles:
        logger.warning("Invalid or missing chat profile: %s", chat_profile)
    profiles_agent = default_agent(chat_profile)
    cl.user_session.set("profiles_agent", profiles_agent)

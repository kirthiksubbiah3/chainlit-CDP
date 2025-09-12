from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage

from .observability_agent import Observability
from .pod_restart_agent import PodRestartAgent
from .cryptowallet_agent import Cryptowallet
from .react_repo_agent import react_repo_agent
from .base_agent import get_all_message_content


class SupervisorInput(BaseModel):
    messages: List[HumanMessage] = Field(default=None, description="Conversation messages so far")
    thread_id: str | None = Field(default=None, description="Conversation thread ID")
    session_type: str | None = Field(default=None, description="Optional session type override")


class SupervisorAgent:
    def __init__(self, llm):
        self.llm = llm
        self.agents = {
            "NewRepo": react_repo_agent,
            "observability": Observability,
            "pod_restart": PodRestartAgent,
            "crypto_wallet": Cryptowallet
        }
        # TODO change the description for each agent inorder to match with the user prompt
        self.description = {
            "NewRepo": "create new git repo with boilerplate code",
            "observability": "metrics, logs, tracing, monitoring, details about Pods, memory, "
                             "affected resources, recommend solutions, alert, slack, cluster ",
            "pod_restart": "restarting pods (EKS/AKS)",
            "crypto_wallet": ("cryptowallet application, crypto wallets created, transaction "
                              "happened, deposited, withdraw, transfer, errors, get, walletID, "
                              "delete, currency, money, error details")
        }

    async def classify_session(self, message: str):
        """
        Use LLM to classify which agent should handle this message.
        """
        desc_lines = [f"- {k}: {v}" for k, v in self.description.items()]
        system_prompt = (
            "You are a router. Classify the user message into one of the categories:\n"
            + "\n".join(desc_lines)
            + f"\nRespond with ONLY the session type from {self.agents.keys()}."
        )
        result = await self.llm.ainvoke([SystemMessage(content=system_prompt),
                                         HumanMessage(content=message)])
        return result.content.strip()

    async def run(self, messages, thread_id: str = None,
                  session_type: str = None):
        """
        Routes user queries to the correct agent.
        """
        # Determine session_type based on query
        if not isinstance(messages, list):
            messages = [HumanMessage(content=messages)]
        msg = get_all_message_content(messages)
        if not session_type:
            session_type = await self.classify_session(msg)
        if session_type not in self.agents:
            raise ValueError(f"Unknown session_type: {session_type}")
        if session_type == "NewRepo":
            resp = await react_repo_agent.ainvoke(
                {"thread_id": thread_id, "llm": self.llm, "new_msg": msg}
            )
            return resp["usage_totals"]
        else:
            agent = self.agents[session_type]()
            return await agent.custom_graph_agent(messages, self.llm, thread_id)

    def as_tool(self):

        desc_lines = [f"- {k}: {v}" for k, v in self.description.items()]
        description = (
                "Supervisor router tool. You MUST call this tool if the user request is"
                "about any of the following categories:\n"
                + "\n".join(desc_lines)
                + "\nDo not answer directly. Always call this tool.."
        )
        return StructuredTool.from_function(
            coroutine=self.run,
            args_schema=SupervisorInput,
            name="supervisor",
            description=description,
        )

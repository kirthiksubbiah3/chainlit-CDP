import asyncio

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from tools_manager import initialize_tools

memory = MemorySaver()


def get_agent(llm):
    return create_react_agent(llm, asyncio.run(initialize_tools()), checkpointer=memory)

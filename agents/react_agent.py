import asyncio

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from tools_manager import initialize_tools
from vars import llm

memory = MemorySaver()
agent = create_react_agent(llm, asyncio.run(initialize_tools()), checkpointer=memory)

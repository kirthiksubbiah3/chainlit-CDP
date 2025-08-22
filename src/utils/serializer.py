from langchain_core.messages import ToolMessage
from langgraph.checkpoint.serde import jsonplus

_original_default = jsonplus._msgpack_default


def _custom_msgpack_default(obj):
    if isinstance(obj, ToolMessage):
        return {
            "type": "tool",
            "content": obj.content,
            "name": obj.name,
            "id": str(obj.id),
            "tool_call_id": obj.tool_call_id,
            "artifact": str(obj.artifact),
        }
    return _original_default(obj)

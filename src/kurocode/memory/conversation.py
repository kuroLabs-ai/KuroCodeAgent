"""Compatibility wrapper for conversation memory."""

from kurocode.core.memory import get_formatted_context, load_memory, save_memory


def load_conversation_memory(limit: int = 20):
    return load_memory()[-limit:]


def save_conversation_memory(user_input: str, response: str, metadata=None):
    return save_memory(user_input, response, metadata)


__all__ = ["load_conversation_memory", "save_conversation_memory", "load_memory", "save_memory", "get_formatted_context"]

"""Compatibility wrapper for user memory."""

from kurocode.core.memory import get_formatted_context, load_memory


def load_user_memory(limit: int = 20):
    return load_memory()[-limit:]


__all__ = ["load_user_memory", "load_memory", "get_formatted_context"]

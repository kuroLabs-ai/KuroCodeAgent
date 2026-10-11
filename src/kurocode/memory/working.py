"""Compatibility wrapper for working memory."""

from kurocode.core.memory import get_formatted_context, load_memory


def load_working_memory(limit: int = 20):
    return load_memory()[-limit:]


__all__ = ["load_working_memory", "load_memory", "get_formatted_context"]

"""Compatibility wrapper for memory retrieval."""

from kurocode.core.memory import get_formatted_context, load_memory


def retrieve_memory(limit: int = 20):
    return load_memory()[-limit:]


__all__ = ["retrieve_memory", "load_memory", "get_formatted_context"]

"""Compatibility wrapper for memory storage."""

from kurocode.core.memory import clear_memory, load_memory, save_memory


def persist_memory(user_input: str, response: str, metadata=None):
    save_memory(user_input, response, metadata)
    return True


__all__ = ["persist_memory", "load_memory", "save_memory", "clear_memory"]

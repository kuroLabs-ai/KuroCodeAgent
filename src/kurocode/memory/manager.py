"""Compatibility wrapper for memory management."""

from kurocode.core.memory import clear_memory, get_formatted_context, load_memory, save_memory


class MemoryManager:
    def load(self, limit: int = 20):
        return load_memory()[-limit:]

    def save(self, user_input: str, response: str, metadata=None):
        save_memory(user_input, response, metadata)
        return True

    def clear(self):
        return clear_memory()


__all__ = ["MemoryManager", "load_memory", "save_memory", "clear_memory", "get_formatted_context"]

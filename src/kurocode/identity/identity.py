"""Compatibility wrapper for identity metadata."""

from kurocode.core.personality import get_system_personality_prompt, load_personality, update_personality

__all__ = [
    "load_personality",
    "update_personality",
    "get_system_personality_prompt",
]

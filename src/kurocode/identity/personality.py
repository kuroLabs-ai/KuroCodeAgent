"""Compatibility wrapper for the system personality module."""

from kurocode.core.personality import (
    DEFAULT_PERSONALITY,
    ensure_brain_dir,
    get_system_personality_prompt,
    load_personality,
    update_personality,
)

__all__ = [
    "DEFAULT_PERSONALITY",
    "ensure_brain_dir",
    "load_personality",
    "update_personality",
    "get_system_personality_prompt",
]

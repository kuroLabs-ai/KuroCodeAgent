"""Context builder aligned with the PRD architecture."""

from __future__ import annotations

from typing import Any, Dict, Optional

from kurocode.core.context_engine import context_engine


class ContextBuilder:
    """Thin adapter over the existing context engine."""

    def __init__(self, max_tokens: int = 3000):
        self.engine = context_engine
        self.engine.max_tokens = max_tokens

    def build(self, user_input: str, task_goal: Optional[str] = None, task_id: Optional[str] = None, **kwargs: Any) -> str:
        return self.engine.build(user_input=user_input, task_goal=task_goal or user_input, task_id=task_id, **kwargs)


__all__ = ["ContextBuilder", "context_engine"]

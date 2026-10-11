"""Provider router façade for the PRD architecture."""

from __future__ import annotations

from typing import Optional, Tuple

from kurocode.core.model_router import TaskType, model_router


class BrainRouter:
    """Wraps the existing model router in a PRD-style abstraction."""

    def __init__(self):
        self._router = model_router

    def route(self, prompt: str, preferred_provider: Optional[str] = None, **kwargs) -> Tuple[str, str, TaskType]:
        return self._router.select_route(prompt, preferred_provider=preferred_provider, **kwargs)


__all__ = ["BrainRouter", "TaskType", "model_router"]

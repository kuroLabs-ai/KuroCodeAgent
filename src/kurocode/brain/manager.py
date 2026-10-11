"""Brain manager and provider registry for the PRD architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kurocode.core.model_router import model_router
from .base import BaseLLMProvider, LLMProvider


@dataclass
class ProviderRegistry:
    providers: Dict[str, LLMProvider] = field(default_factory=dict)

    def register(self, provider: LLMProvider) -> None:
        self.providers[provider.name] = provider

    def get(self, name: str) -> Optional[LLMProvider]:
        return self.providers.get(name)

    def available(self) -> List[str]:
        return sorted(self.providers.keys())


class BrainManager:
    """Coordinates a provider registry and task-aware routing."""

    def __init__(self):
        self.registry = ProviderRegistry()
        self.default_provider = "base"

    def register(self, provider: LLMProvider) -> None:
        self.registry.register(provider)

    def select(self, prompt: str, preferred_provider: Optional[str] = None, **kwargs: Any) -> tuple[str, str, Any]:
        provider, model, task_type = model_router.select_route(prompt, preferred_provider=preferred_provider, **kwargs)
        return provider, model, task_type

    def health_check(self) -> Dict[str, bool]:
        checks: Dict[str, bool] = {}
        for name, provider in self.registry.providers.items():
            try:
                checks[name] = bool(provider.health_check())
            except Exception:
                checks[name] = False
        return checks


__all__ = ["BrainManager", "ProviderRegistry", "LLMProvider", "BaseLLMProvider", "model_router"]

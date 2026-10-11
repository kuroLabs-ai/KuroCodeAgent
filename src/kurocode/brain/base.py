"""LLM provider abstraction for the PRD architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kurocode.core.model_router import model_router


class LLMProvider:
    """Abstract interface for provider adapters."""

    name: str = "base"
    models: List[str] = field(default_factory=list)

    def authenticate(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def health_check(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, **kwargs: Any):
        raise NotImplementedError

    @property
    def usage(self) -> Dict[str, Any]:
        return {}


@dataclass
class BaseLLMProvider(LLMProvider):
    name: str = "base"
    models: List[str] = field(default_factory=list)

    def authenticate(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def health_check(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        return f"[provider:{self.name}] {prompt[:200]}"

    def stream(self, prompt: str, **kwargs: Any):
        yield self.generate(prompt, **kwargs)


__all__ = ["LLMProvider", "BaseLLMProvider", "model_router"]

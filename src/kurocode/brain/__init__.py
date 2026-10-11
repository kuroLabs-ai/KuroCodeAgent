"""Brain package with provider-abstraction entry points.

The project already has a model router, but this package adds the provider
layer described in the PRD and keeps compatibility with current code.
"""

from kurocode.core.model_router import model_router
from .base import LLMProvider, BaseLLMProvider
from .manager import BrainManager, ProviderRegistry

__all__ = [
    "model_router",
    "LLMProvider",
    "BaseLLMProvider",
    "BrainManager",
    "ProviderRegistry",
]

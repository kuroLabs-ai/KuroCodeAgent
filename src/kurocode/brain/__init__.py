"""Brain package with provider-abstraction entry points.

The project already has a model router, but this package adds the provider
layer described in the PRD and keeps compatibility with current code.
"""

from kurocode.core.model_router import model_router
from .base import LLMProvider, BaseLLMProvider
from .manager import BrainManager, ProviderRegistry
from .models import (
    ModelSpec,
    get_model_catalog,
    list_providers,
    get_provider_spec,
    get_models_for_provider,
    list_all_models,
)

__all__ = [
    "model_router",
    "LLMProvider",
    "BaseLLMProvider",
    "BrainManager",
    "ProviderRegistry",
    "ModelSpec",
    "get_model_catalog",
    "list_providers",
    "get_provider_spec",
    "get_models_for_provider",
    "list_all_models",
]


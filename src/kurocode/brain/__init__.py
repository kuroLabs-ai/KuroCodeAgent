"""Brain package with provider-abstraction entry points.

The project already has a model router, but this package adds the provider
layer described in the PRD and keeps compatibility with current code.
"""

from kurocode.core.model_router import model_router
from .base import LLMProvider, BaseLLMProvider
from .manager import BrainManager, ProviderRegistry
from .models import (
    ModelSpec,
    get_model_kurohub,
    list_providers,
    get_provider_spec,
    get_models_for_provider,
    list_all_models,
)

from .kuro_hub import (
    get_tools_kurohub,
    get_plugins_kurohub,
    get_skills_kurohub,
    get_integrations_kurohub,
    register_tool_in_json,
    unregister_tool_from_json,
    register_plugin_in_json,
    unregister_plugin_from_json,
    register_skill_in_json,
    unregister_skill_from_json,
    register_integration_in_json,
    unregister_integration_from_json,
)

__all__ = [
    "model_router",
    "LLMProvider",
    "BaseLLMProvider",
    "BrainManager",
    "ProviderRegistry",
    "ModelSpec",
    "get_model_kurohub",
    "list_providers",
    "get_provider_spec",
    "get_models_for_provider",
    "list_all_models",
    "get_tools_kurohub",
    "get_plugins_kurohub",
    "get_skills_kurohub",
    "get_integrations_kurohub",
    "register_tool_in_json",
    "unregister_tool_from_json",
    "register_plugin_in_json",
    "unregister_plugin_from_json",
    "register_skill_in_json",
    "unregister_skill_from_json",
    "register_integration_in_json",
    "unregister_integration_from_json",
]


"""Model metadata and registry for the KURO brain layer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModelSpec:
    name: str
    provider: str
    capabilities: List[str] = field(default_factory=list)
    context_window: int = 128000


_MODELS_JSON_PATH = Path(__file__).parent / "models.json"


def get_model_catalog() -> Dict[str, Any]:
    """Loads and returns the complete models.json registry catalog."""
    if _MODELS_JSON_PATH.exists():
        try:
            return json.loads(_MODELS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def list_providers() -> List[str]:
    """Returns list of all configured provider names in the catalog."""
    catalog = get_model_catalog()
    return list(catalog.get("providers", {}).keys())


def get_provider_spec(provider: str) -> Optional[Dict[str, Any]]:
    """Returns the registry entry for a specific provider."""
    catalog = get_model_catalog()
    return catalog.get("providers", {}).get(provider.lower())


def get_models_for_provider(provider: str) -> List[str]:
    """Returns list of model names supported by the specified provider."""
    spec = get_provider_spec(provider)
    if spec:
        return spec.get("models", [])
    return []


def list_all_models() -> Dict[str, List[str]]:
    """Returns a dict mapping provider name to its list of models."""
    catalog = get_model_catalog()
    return {
        prov: data.get("models", [])
        for prov, data in catalog.get("providers", {}).items()
    }


__all__ = [
    "ModelSpec",
    "get_model_catalog",
    "list_providers",
    "get_provider_spec",
    "get_models_for_provider",
    "list_all_models",
]


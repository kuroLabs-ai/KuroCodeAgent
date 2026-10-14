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


def get_model_kurohub() -> Dict[str, Any]:
    """Loads and returns the complete models.json registry catalog."""
    if _MODELS_JSON_PATH.exists():
        try:
            return json.loads(_MODELS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def list_providers() -> List[str]:
    """Returns list of all configured provider names in KuroHub."""
    kurohub = get_model_kurohub()
    return list(kurohub.get("providers", {}).keys())


def get_provider_spec(provider: str) -> Optional[Dict[str, Any]]:
    """Returns the registry entry for a specific provider."""
    kurohub = get_model_kurohub()
    return kurohub.get("providers", {}).get(provider.lower())


def get_models_for_provider(provider: str) -> List[str]:
    """Returns list of model names supported by the specified provider."""
    spec = get_provider_spec(provider)
    if spec:
        return spec.get("models", [])
    return []


def list_all_models() -> Dict[str, List[str]]:
    """Returns a dict mapping provider name to its list of models."""
    kurohub = get_model_kurohub()
    return {
        prov: data.get("models", [])
        for prov, data in kurohub.get("providers", {}).items()
    }


__all__ = [
    "ModelSpec",
    "get_model_kurohub",
    "list_providers",
    "get_provider_spec",
    "get_models_for_provider",
    "list_all_models",
]


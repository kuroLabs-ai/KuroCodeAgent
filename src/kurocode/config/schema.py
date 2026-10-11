"""Schema helper for config validation."""

from __future__ import annotations

from typing import Any, Dict, Iterable


def validate_config(cfg: Dict[str, Any]) -> Iterable[str]:
    errors: list[str] = []
    if not isinstance(cfg.get("provider"), str):
        errors.append("provider must be a string")
    if not isinstance(cfg.get("model"), str):
        errors.append("model must be a string")
    return errors


__all__ = ["validate_config"]

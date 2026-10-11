"""Simple configuration manager."""

from __future__ import annotations

from typing import Any, Dict

from .defaults import DEFAULT_CONFIG


class ConfigManager:
    """Loads and updates runtime config values."""

    def __init__(self, initial: Dict[str, Any] | None = None):
        self.config = dict(DEFAULT_CONFIG)
        if initial:
            self.config.update(initial)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.config)


__all__ = ["ConfigManager"]

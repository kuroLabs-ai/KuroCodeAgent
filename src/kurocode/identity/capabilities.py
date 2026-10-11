"""Compatibility wrapper for identity capability metadata."""

from typing import Any, Dict

DEFAULT_CAPABILITIES: Dict[str, Any] = {
    "memory": True,
    "browser": True,
    "plugins": True,
    "tools": True,
    "security": True,
}


def get_capabilities() -> Dict[str, Any]:
    return dict(DEFAULT_CAPABILITIES)


__all__ = ["DEFAULT_CAPABILITIES", "get_capabilities"]

"""Compatibility wrapper for tool results."""

from typing import Any, Dict


def result_ok(**payload: Any) -> Dict[str, Any]:
    data = {"success": True}
    data.update(payload)
    return data


def result_error(message: str, **payload: Any) -> Dict[str, Any]:
    data = {"success": False, "error": message}
    data.update(payload)
    return data


__all__ = ["result_ok", "result_error"]

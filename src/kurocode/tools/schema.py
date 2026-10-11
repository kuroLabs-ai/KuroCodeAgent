"""Compatibility wrapper for tool schemas."""

from kurocode.core.plugin_registry import registry


def get_tool_schemas():
    return registry.generate_system_tool_schemas()


__all__ = ["get_tool_schemas", "registry"]

"""Compatibility wrapper for dynamic tool loading."""

from kurocode.core.plugin_registry import registry


def load_tools(plugins_dir=None):
    return registry.load_user_plugins(plugins_dir)


__all__ = ["load_tools", "registry"]

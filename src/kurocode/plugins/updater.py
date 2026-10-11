"""Plugin update hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class PluginUpdater:
    """Very small updater abstraction for future plugin publishing."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def update(self, plugin_name: str) -> Dict[str, Any]:
        plugin_dir = self.repo_root / plugin_name
        if not plugin_dir.exists():
            return {"success": False, "error": "Plugin not found."}
        return {"success": True, "plugin": plugin_name, "path": str(plugin_dir)}


__all__ = ["PluginUpdater"]

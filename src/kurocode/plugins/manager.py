"""Plugin manager for discovery, installation, and registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from kurocode.core.paths import PLUGINS_DIR
from kurocode.core.plugin_registry import registry
from .loader import PluginLoader
from .validator import PluginValidator
from .installer import PluginInstaller


class PluginManager:
    """High-level plugin discovery, installation, and lifecycle manager."""

    def __init__(self, plugins_dir: Optional[Path] = None, plugin_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or plugin_dir or PLUGINS_DIR
        self.loader = PluginLoader(registry)
        self.validator = PluginValidator()
        self.installer = PluginInstaller()
        self.plugins: Dict[str, Dict[str, Any]] = {}

    def discover(self) -> List[Path]:
        if not self.plugins_dir.exists():
            return []
        return sorted([p for p in self.plugins_dir.iterdir() if p.is_dir()])

    def load_all(self) -> Dict[str, Any]:
        loaded: Dict[str, Any] = {}
        for plugin_dir in self.discover():
            res = self.loader.load_from_dir(plugin_dir)
            if res.get("success"):
                loaded[res["plugin"]] = res
        self.plugins = loaded
        return loaded

    def install(self, plugin_name: str, source_dir: Path) -> Dict[str, Any]:
        res = self.installer.install(plugin_name, source_dir, self.plugins_dir)
        if not res.get("success"):
            return res
        return self.loader.load_from_dir(self.plugins_dir / plugin_name)

    def install_from_source(self, source: str, name: Optional[str] = None) -> Dict[str, Any]:
        res = self.installer.install_from_source(source, self.plugins_dir, plugin_name=name)
        if not res.get("success"):
            return res
        installed_name = res.get("name")
        if installed_name:
            load_res = self.loader.load_from_dir(self.plugins_dir / installed_name)
            return {**res, "load_result": load_res}
        return res

    def uninstall(self, plugin_name: str) -> bool:
        plugin_dir = self.plugins_dir / plugin_name
        if not plugin_dir.exists():
            # Check by manifest name in subdirectories
            for d in self.plugins_dir.iterdir():
                if d.is_dir() and (d / "plugin.json").exists():
                    try:
                        m = json.loads((d / "plugin.json").read_text(encoding="utf-8"))
                        if m.get("name") == plugin_name:
                            plugin_dir = d
                            break
                    except Exception:
                        pass
        if not plugin_dir.exists():
            return False
        import shutil
        shutil.rmtree(plugin_dir, ignore_errors=True)
        self.plugins.pop(plugin_name, None)
        return True

    def uninstall_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Convenience method returning a result dict."""
        ok = self.uninstall(plugin_name)
        if ok:
            return {"success": True, "plugin": plugin_name}
        return {"success": False, "error": f"Plugin '{plugin_name}' not found."}

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Discovers and returns metadata dictionaries for all installed plugins."""
        self.load_all()
        results = []
        for name, data in self.plugins.items():
            manifest = data.get("manifest", {})
            results.append({
                "name": name,
                "version": manifest.get("version", "1.0.0"),
                "description": manifest.get("description", ""),
                "enabled": True,
                **manifest,
            })
        return results


plugin_manager = PluginManager()

__all__ = ["PluginManager", "plugin_manager"]

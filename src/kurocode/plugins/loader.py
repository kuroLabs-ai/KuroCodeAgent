"""Plugin loader for registry integration."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from kurocode.core.plugin_registry import registry
from .manifest import PluginManifest
from .validator import PluginValidator


class PluginLoader:
    """Loads plugin directories into the shared registry."""

    def __init__(self, registry_ref=None):
        self.registry_ref = registry_ref or registry
        self.validator = PluginValidator()

    def load_from_dir(self, plugin_dir: Path) -> Dict[str, Any]:
        validation = self.validator.validate(plugin_dir)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        with open(plugin_dir / "plugin.json", "r", encoding="utf-8") as fh:
            manifest_data = json.load(fh)

        errors = self.validator.validate_manifest(manifest_data)
        if errors:
            return {"success": False, "error": "; ".join(errors)}

        module_name = f"kuro_plugin_{plugin_dir.name}"
        plugin_path = plugin_dir / manifest_data.get("entrypoint", "plugin.py")
        spec = importlib.util.spec_from_file_location(module_name, str(plugin_path))
        if spec is None or spec.loader is None:
            return {"success": False, "error": f"Could not load plugin entrypoint for {plugin_dir.name}."}

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        register_fn = getattr(module, "register", None)
        if callable(register_fn):
            register_fn(self.registry_ref)

        manifest = PluginManifest.from_dict(manifest_data)
        return {
            "success": True,
            "plugin": manifest.name,
            "manifest": manifest.to_dict(),
            "module": module_name,
        }


__all__ = ["PluginLoader"]

"""Plugin validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class PluginValidator:
    """Checks that a plugin directory contains the required structure."""

    def validate(self, plugin_dir: Path) -> Dict[str, Any]:
        if not plugin_dir.exists():
            return {"valid": False, "error": "Plugin directory does not exist."}

        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.exists():
            return {"valid": False, "error": "Missing plugin.json manifest."}

        ep_name = "plugin.py"
        try:
            import json
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            ep_name = m.get("entrypoint", "plugin.py")
        except Exception:
            pass

        py_path = plugin_dir / ep_name
        if not py_path.exists():
            py_path = plugin_dir / "plugin.py"
        if not py_path.exists():
            py_path = plugin_dir / "main.py"
        if not py_path.exists():
            return {"valid": False, "error": f"Missing entrypoint script ({ep_name})."}

        return {"valid": True, "manifest": str(manifest_path), "entrypoint": str(py_path)}

    def validate_dir(self, plugin_dir: Path) -> Dict[str, Any]:
        """Alias for validate."""
        return self.validate(plugin_dir)

    def validate_manifest(self, manifest_data: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        if not manifest_data.get("name"):
            errors.append("Plugin manifest missing 'name'.")
        if not manifest_data.get("version"):
            errors.append("Plugin manifest missing 'version'.")
        if not manifest_data.get("entrypoint"):
            errors.append("Plugin manifest missing 'entrypoint'.")
        return errors


__all__ = ["PluginValidator"]

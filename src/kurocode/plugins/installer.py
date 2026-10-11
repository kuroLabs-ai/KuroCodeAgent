"""
src/kurocode/plugins/installer.py — Plugin Installation Engine.
Supports installing plugins from local directories, zip archives, or Git repositories.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .validator import PluginValidator


class PluginInstaller:
    """Installs external plugins into the KuroCode plugins directory."""

    def __init__(self):
        self.validator = PluginValidator()

    def install(self, name: str, source_dir: Path, target_dir: Path) -> Dict[str, Any]:
        """Installs from an existing local folder."""
        target = target_dir / name
        if target.exists():
            return {"success": False, "error": f"Plugin '{name}' is already installed."}

        # Validate before copying
        val = self.validator.validate_dir(source_dir)
        if not val.get("valid"):
            return {"success": False, "error": f"Plugin validation failed: {val.get('error')}"}

        target.mkdir(parents=True, exist_ok=True)
        for item in source_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, target / item.name)
            else:
                shutil.copy2(item, target / item.name)

        return {"success": True, "name": name, "path": str(target)}

    def install_from_source(self, source: str, target_dir: Path, plugin_name: Optional[str] = None) -> Dict[str, Any]:
        """Installs from a directory path or Git clone URL."""
        source_path = Path(source)
        if source_path.exists() and source_path.is_dir():
            name = plugin_name or source_path.name
            return self.install(name, source_path, target_dir)

        # Git clone support
        if source.startswith(("http://", "https://", "git@")) or source.endswith(".git"):
            name = plugin_name or source.rstrip("/").split("/")[-1].replace(".git", "")
            target = target_dir / name
            if target.exists():
                return {"success": False, "error": f"Plugin '{name}' already exists in target directory."}
            try:
                cmd = ["git", "clone", "--depth", "1", source, str(target)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    return {"success": False, "error": f"Git clone failed: {res.stderr}"}
                val = self.validator.validate_dir(target)
                if not val.get("valid"):
                    shutil.rmtree(target, ignore_errors=True)
                    return {"success": False, "error": f"Cloned plugin is invalid: {val.get('error')}"}
                return {"success": True, "name": name, "path": str(target)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Invalid source '{source}'. Must be local directory or Git URL."}


__all__ = ["PluginInstaller"]

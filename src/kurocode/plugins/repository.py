"""Repository abstraction for plugin discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


class PluginRepository:
    """A simple file-based repository for local plugins."""

    def __init__(self, root: Path):
        self.root = root

    def list_plugins(self) -> List[str]:
        if not self.root.exists():
            return []
        return sorted([p.name for p in self.root.iterdir() if p.is_dir()])

    def iter_plugin_dirs(self) -> Iterable[Path]:
        if not self.root.exists():
            return []
        return [p for p in self.root.iterdir() if p.is_dir()]


__all__ = ["PluginRepository"]

"""Workspace metadata container."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class WorkspaceInfo:
    root: Path
    name: str
    python_projects: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, root: str | Path) -> "WorkspaceInfo":
        root_path = Path(root)
        projects = []
        if root_path.exists():
            for child in sorted(root_path.iterdir()):
                if child.is_dir() and (child / "pyproject.toml").exists():
                    projects.append(child.name)
        return cls(root=root_path, name=root_path.name, python_projects=projects)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "name": self.name,
            "python_projects": self.python_projects,
            "metadata": self.metadata,
        }


__all__ = ["WorkspaceInfo"]

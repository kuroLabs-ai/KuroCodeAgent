"""Project profile detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ProjectProfile:
    root: Path
    name: str
    language: str = "python"
    framework: str = "unknown"
    files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, root: str | Path) -> "ProjectProfile":
        path = Path(root)
        name = path.name or "workspace"
        language = "python" if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists() else "unknown"
        framework = "django" if (path / "manage.py").exists() else "unknown"
        files = []
        for child in sorted(path.iterdir()):
            if child.is_file() and child.suffix in {".py", ".md", ".toml", ".json", ".yml", ".yaml"}:
                files.append(child.name)
        return cls(root=path, name=name, language=language, framework=framework, files=files)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "name": self.name,
            "language": self.language,
            "framework": self.framework,
            "files": self.files,
            "metadata": self.metadata,
        }


__all__ = ["ProjectProfile"]

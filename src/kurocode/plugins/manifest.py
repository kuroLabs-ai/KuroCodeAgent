"""Plugin manifest helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PluginManifest:
    name: str
    version: str = "0.1.0"
    description: str = ""
    entrypoint: str = "plugin.py"
    requires: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        return cls(
            name=data.get("name", "unnamed-plugin"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            entrypoint=data.get("entrypoint", "plugin.py"),
            requires=data.get("requires", []),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entrypoint": self.entrypoint,
            "requires": self.requires,
            "permissions": self.permissions,
            "metadata": self.metadata,
        }


__all__ = ["PluginManifest"]

"""
src/kurocode/store/models.py — Data models for the Kuro Puzzle Store / Hub.
Defines installable puzzle pieces (Tools, Plugins, Skills, Integrations).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StoreItemType(str, Enum):
    TOOL = "tool"
    PLUGIN = "plugin"
    SKILL = "skill"
    INTEGRATION = "integration"


@dataclass
class StoreItem:
    """Represents an installable puzzle-piece capability in the Kuro Store."""
    id: str
    name: str
    item_type: StoreItemType
    description: str
    version: str = "1.0.0"
    author: str = "Kuro Hub"
    tags: List[str] = field(default_factory=list)
    file_path: Optional[str] = None          # tools only — single .py file path in hub repo
    dir_path: Optional[str] = None           # plugins / skills / integrations — folder path in hub repo
    payload: Dict[str, Any] = field(default_factory=dict)
    installed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "item_type": self.item_type.value,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "payload": self.payload,
            "installed": self.installed,
        }
        if self.file_path:
            data["file_path"] = self.file_path
        if self.dir_path:
            data["dir_path"] = self.dir_path
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StoreItem:
        raw_type = data.get("item_type", "tool")
        item_type = StoreItemType(raw_type) if raw_type in StoreItemType._value2member_map_ else StoreItemType.TOOL
        payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}
        file_path = data.get("file_path") or payload.get("file_path")
        dir_path = data.get("dir_path") or payload.get("dir_path")
        return cls(
            id=data.get("id", data.get("name", "")),
            name=data.get("name", ""),
            item_type=item_type,
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Kuro Hub"),
            tags=data.get("tags", []),
            file_path=file_path,
            dir_path=dir_path,
            payload=payload,
            installed=data.get("installed", False),
        )


__all__ = ["StoreItemType", "StoreItem"]

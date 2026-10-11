"""Event model for the PRD orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from kurocode.core.io_bus import CoreEvent, EventKind, EventLevel, InputRequest, IOHost, NullHost


@dataclass
class AgentEvent:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    level: str = "INFO"
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        data = {"name": self.name, "level": self.level, "timestamp": self.timestamp.isoformat()}
        data.update(self.payload)
        return data


__all__ = [
    "AgentEvent",
    "CoreEvent",
    "EventKind",
    "EventLevel",
    "InputRequest",
    "IOHost",
    "NullHost",
]

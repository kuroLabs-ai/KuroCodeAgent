"""Audit log helpers for security actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class AuditEvent:
    action: str
    actor: str = "kuro"
    result: str = "ok"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class AuditTrail:
    """Simple in-memory audit trail used by security checks."""

    def __init__(self):
        self.events: List[AuditEvent] = []

    def record(self, action: str, result: str = "ok", **details: Any) -> AuditEvent:
        event = AuditEvent(action=action, result=result, details=details)
        self.events.append(event)
        return event

    def list(self) -> List[Dict[str, Any]]:
        return [event.__dict__ for event in self.events]


__all__ = ["AuditEvent", "AuditTrail"]

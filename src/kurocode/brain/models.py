"""Model metadata for the PRD brain layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ModelSpec:
    name: str
    provider: str
    capabilities: List[str] = field(default_factory=list)
    context_window: int = 128000


__all__ = ["ModelSpec"]

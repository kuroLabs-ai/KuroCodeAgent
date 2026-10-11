"""Goal tracking model aligned with the PRD."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid


class GoalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Goal:
    text: str
    goal_id: Optional[str] = None
    status: GoalStatus = GoalStatus.PENDING
    parent_id: Optional[str] = None
    subgoals: List["Goal"] = field(default_factory=list)
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.goal_id:
            self.goal_id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.utcnow()

    def mark_in_progress(self) -> None:
        self.status = GoalStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def mark_failed(self, reason: str = "") -> None:
        self.status = GoalStatus.FAILED
        self.completed_at = datetime.utcnow()

    def add_subgoal(self, goal: "Goal") -> None:
        goal.parent_id = self.goal_id
        self.subgoals.append(goal)


__all__ = ["Goal", "GoalStatus"]

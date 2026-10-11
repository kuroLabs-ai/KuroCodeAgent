"""Planning layer aligned with the PRD.

This keeps the repository's existing planner utilities while exposing a more
explicit `Planner` interface that matches the architecture described in the
prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kurocode.tools.planner import create_task_plan, format_plan_table


@dataclass
class PlanStep:
    name: str
    description: str
    status: str = "pending"


class Planner:
    """Creates and formats execution plans for a goal."""

    def __init__(self, llm_fn=None):
        self.llm_fn = llm_fn

    def create(self, goal: str, **kwargs: Any) -> Dict[str, Any]:
        """Create a plan using the repository's existing task planner."""
        plan = create_task_plan(goal, llm_fn=self.llm_fn, **kwargs)
        return plan or {"id": "plan-0", "goal": goal, "status": "pending", "steps": []}

    def format(self, plan: Dict[str, Any]) -> str:
        return format_plan_table(plan)


__all__ = ["Planner", "PlanStep", "create_task_plan", "format_plan_table"]

"""KuroCode core package.

This package exposes the runtime architecture described by the PRD while
remaining compatible with the repository's existing implementations.
"""

from kurocode.core.agent import KuroAgent
Agent = KuroAgent
from .orchestrator import KuroOrchestrator
from .state import AgentState, AgentStateMachine
from .goals import Goal, GoalStatus
from .planner import Planner
from .evaluator import Evaluator
from .loop import AgentLoop

__all__ = [
    "KuroAgent",
    "Agent",
    "KuroOrchestrator",
    "AgentState",
    "AgentStateMachine",
    "Goal",
    "GoalStatus",
    "Planner",
    "Evaluator",
    "AgentLoop",
]

"""Runtime state model for the PRD architecture.

This module adds the explicit state machine described in the prompt while
keeping compatibility with the repository's `core.task_state` implementation.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from kurocode.core.task_state import TaskState, task_registry


class AgentState(str, Enum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    EVALUATING = "EVALUATING"
    WAITING = "WAITING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class AgentStateMachine:
    """Small state machine used by the PRD orchestrator layer."""

    _TRANSITIONS: Dict[AgentState, tuple[AgentState, ...]] = {
        AgentState.IDLE: (AgentState.THINKING, AgentState.PLANNING),
        AgentState.THINKING: (AgentState.PLANNING, AgentState.EXECUTING, AgentState.WAITING),
        AgentState.PLANNING: (AgentState.EXECUTING, AgentState.FAILED),
        AgentState.EXECUTING: (AgentState.OBSERVING, AgentState.FAILED),
        AgentState.OBSERVING: (AgentState.EVALUATING, AgentState.EXECUTING),
        AgentState.EVALUATING: (AgentState.COMPLETED, AgentState.FAILED, AgentState.WAITING),
        AgentState.WAITING: (AgentState.THINKING, AgentState.EXECUTING, AgentState.FAILED),
        AgentState.FAILED: (AgentState.IDLE,),
        AgentState.COMPLETED: (AgentState.IDLE,),
    }

    def __init__(self, initial: AgentState = AgentState.IDLE):
        self.state = initial

    def set_state(self, state: AgentState) -> bool:
        allowed = self._TRANSITIONS.get(self.state, ())
        if state not in allowed and self.state != AgentState.IDLE:
            if state != self.state:
                raise ValueError(f"Invalid transition from {self.state.value} to {state.value}")
        self.state = state
        return True

    def is_terminal(self) -> bool:
        return self.state in (AgentState.FAILED, AgentState.COMPLETED)

    def reset(self) -> None:
        self.state = AgentState.IDLE


__all__ = ["AgentState", "AgentStateMachine", "TaskState", "task_registry"]

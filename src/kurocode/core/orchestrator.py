"""Central orchestrator for the PRD architecture.

This orchestrates the existing agent, planner, and evaluator modules while
keeping the repository's current implementation intact.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from kurocode.core.agent import KuroAgent
from .state import AgentState, AgentStateMachine
from .planner import Planner
from .evaluator import Evaluator


class KuroOrchestrator:
    """Small orchestrator that coordinates planning and execution."""

    def __init__(self, agent: Optional[KuroAgent] = None):
        self.agent = agent or KuroAgent()
        self.state = AgentStateMachine()
        self.planner = Planner()
        self.evaluator = Evaluator()

    def run_goal(self, user_input: str, interactive: bool = True) -> str:
        self.state.set_state(AgentState.THINKING)
        plan = self.planner.create(user_input)
        self.state.set_state(AgentState.PLANNING)
        result = self.agent.run(user_input, interactive=interactive)
        self.state.set_state(AgentState.EVALUATING)
        eval_result = self.evaluator.evaluate(user_input, result)
        if eval_result.success:
            self.state.set_state(AgentState.COMPLETED)
        else:
            self.state.set_state(AgentState.FAILED)
        return result

    def create_plan(self, goal: str) -> Dict[str, Any]:
        return self.planner.create(goal)


__all__ = ["KuroOrchestrator"]

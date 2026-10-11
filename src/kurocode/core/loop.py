"""Execution loop facade for the PRD architecture."""

from __future__ import annotations

from typing import Any, Optional

from kurocode.core.agent import KuroAgent


class AgentLoop:
    """Thin compatibility wrapper around the project's operational agent loop."""

    def __init__(self, agent: Optional[KuroAgent] = None):
        self.agent = agent or KuroAgent()

    def run(self, user_input: str, interactive: bool = True) -> str:
        return self.agent.run(user_input, interactive=interactive)


__all__ = ["AgentLoop", "KuroAgent"]

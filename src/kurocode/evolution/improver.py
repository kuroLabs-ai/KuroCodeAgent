"""
src/kurocode/evolution/improver.py — Proposal & Strategy Synthesizer for Self-Improvement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .analyzer import PerformanceInsight


@dataclass
class ImprovementProposal:
    """A structured proposed improvement to agent capabilities."""
    proposal_id: str
    title: str = ""
    description: str = ""
    rationale: str = ""
    target_subsystem: str = "skills"  # "skills", "tools", "prompts", "integrations"
    target_module: str = ""
    action: str = "refactor"
    proposed_changes: List[str] = field(default_factory=list)
    requires_user_approval: bool = True
    status: str = "draft"  # "draft", "testing", "approved", "rejected", "applied"

    def __post_init__(self):
        if not self.description and self.rationale:
            self.description = self.rationale
        elif not self.rationale and self.description:
            self.rationale = self.description
        if not self.title:
            self.title = f"Improvement for {self.target_module or self.target_subsystem}"


class EvolutionImprover:
    """Formulates structured improvements based on analytical insights."""

    def propose_improvement(
        self,
        target_module: str,
        rationale: str,
        action: str = "refactor",
    ) -> ImprovementProposal:
        """Creates a targeted capability enhancement proposal."""
        import uuid
        pid = f"PROP-{uuid.uuid4().hex[:8].upper()}"
        return ImprovementProposal(
            proposal_id=pid,
            title=f"Improvement for {target_module}",
            description=rationale,
            target_subsystem="tools",
            target_module=target_module,
            action=action,
            proposed_changes=[f"{action} on {target_module}: {rationale}"],
        )

    def formulate_proposals(self, insights: List[PerformanceInsight]) -> List[ImprovementProposal]:
        proposals: List[ImprovementProposal] = []
        for idx, insight in enumerate(insights, 1):
            if insight.kind == "repeated_failure":
                proposals.append(
                    ImprovementProposal(
                        proposal_id=f"prop-fail-{idx}",
                        title="Enhance Error Recovery Strategy",
                        description=f"Address repeated failure patterns: {insight.description}",
                        target_subsystem="skills",
                        action="enhance_recovery",
                        proposed_changes=[
                            "Add specialized self-healing strategy",
                            "Record recovery skill routine in skills registry",
                        ],
                        requires_user_approval=True,
                    )
                )
            elif insight.kind == "missing_tool":
                proposals.append(
                    ImprovementProposal(
                        proposal_id=f"prop-tool-{idx}",
                        title="Author New Task Automation Skill",
                        description="Synthesize procedural routine to automate requested unsupported capability.",
                        target_subsystem="tools",
                        action="create_tool",
                        proposed_changes=[
                            "Author dynamic Python tool contract",
                            "Validate through AST safety sandbox",
                            "Register into PluginRegistry",
                        ],
                        requires_user_approval=True,
                    )
                )
        return proposals


__all__ = ["ImprovementProposal", "EvolutionImprover"]

"""
src/kurocode/evolution — Controlled Self-Improvement Subsystem (PRD §41).
Analyzes performance bottlenecks, synthesizes proposed capabilities, and verifies them in isolation.
"""

from __future__ import annotations

import shutil
from typing import Any, Dict, List, Optional

from kurocode.core.paths import SKILLS_DIR
from .analyzer import EvolutionAnalyzer, PerformanceInsight
from .generator import EvolutionGenerator
from .improver import EvolutionImprover, ImprovementProposal
from .tester import EvolutionTester
from .versioning import EvolutionLedger


class EvolutionEngine:
    """Unified coordinator for controlled agent capability evolution."""

    def __init__(self):
        self.analyzer = EvolutionAnalyzer()
        self.improver = EvolutionImprover()
        self.generator = EvolutionGenerator()
        self.tester = EvolutionTester()
        self.ledger = EvolutionLedger()

    def assess_and_propose(self) -> List[ImprovementProposal]:
        """Analyzes recent performance and returns candidate improvement proposals."""
        insights = self.analyzer.analyze_task_history()
        return self.improver.formulate_proposals(insights)

    def run_evolution_cycle(self) -> Dict[str, Any]:
        """Runs an end-to-end performance analysis and formulates an evolution proposal."""
        proposals = self.assess_and_propose()
        if not proposals:
            prop = self.improver.propose_improvement(
                target_module="kurocode.core.agent",
                rationale="Streamline prompt context and tool invocation telemetry.",
                action="optimize_latency",
            )
            self.ledger.record_proposal(prop)
            return {
                "success": True,
                "proposal_id": prop.proposal_id,
                "target_module": prop.target_module,
                "action": prop.action,
                "rationale": prop.description,
                "status": prop.status,
            }

        p = proposals[0]
        self.ledger.record_proposal(p)
        return {
            "success": True,
            "proposal_id": p.proposal_id,
            "target_module": p.target_subsystem,
            "action": p.action,
            "rationale": p.description,
            "status": p.status,
        }

    def apply_skill_proposal(
        self,
        skill_name: str,
        description: str,
        steps: List[str],
    ) -> Dict[str, Any]:
        """Generates, tests, and safely deploys a new skill into the user skills directory."""
        # 1. Generate in isolated workspace
        draft_dir = self.generator.generate_skill_routine(skill_name, description, steps)

        # 2. Test & Validate
        val = self.tester.validate_skill_dir(draft_dir)
        if not val.get("valid"):
            self.generator.cleanup()
            return {"success": False, "error": val.get("error")}

        # 3. Deploy to production skills directory
        target_dir = SKILLS_DIR / skill_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in draft_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, target_dir / item.name)

        self.generator.cleanup()

        # 4. Record evolution ledger entry
        entry = self.ledger.record_evolution(
            proposal_id=f"skill-{skill_name}",
            title=f"Added procedural skill '{skill_name}'",
            changes=steps,
        )

        return {
            "success": True,
            "skill_name": skill_name,
            "version": entry.get("version"),
            "path": str(target_dir),
        }


evolution_engine = EvolutionEngine()

__all__ = [
    "PerformanceInsight",
    "EvolutionAnalyzer",
    "ImprovementProposal",
    "EvolutionImprover",
    "EvolutionGenerator",
    "EvolutionTester",
    "EvolutionLedger",
    "EvolutionEngine",
    "evolution_engine",
]

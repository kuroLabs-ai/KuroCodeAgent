"""
src/kurocode/healing/diagnostician.py — Diagnostic Engine for KuroCode.
Analyzes failure reports to determine root causes and formulate repair hypotheses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .detector import ErrorCategory, FailureReport, FailureSeverity


@dataclass
class Diagnosis:
    """The formulated root cause and recommended repair action."""
    report: FailureReport
    root_cause: str
    suggested_action: str
    confidence: float  # 0.0 to 1.0
    can_auto_heal: bool
    repair_plan: List[str] = field(default_factory=list)


class FailureDiagnostician:
    """Diagnoses failures by checking local environment state and error signatures."""

    def diagnose(self, report: FailureReport) -> Diagnosis:
        category = report.category

        if category == ErrorCategory.MISSING_DEPENDENCY:
            mod = report.missing_module or "dependency"
            return Diagnosis(
                report=report,
                root_cause=f"Required Python module '{mod}' is not installed in the active environment.",
                suggested_action=f"Install module via pip: 'pip install {mod}'",
                confidence=0.95,
                can_auto_heal=True,
                repair_plan=[f"pip install {mod}", "verify installation import", "retry original command"],
            )

        if category == ErrorCategory.SYNTAX_ERROR:
            target = report.target_path or "modified file"
            return Diagnosis(
                report=report,
                root_cause=f"Syntax or indentation error in {target}.",
                suggested_action="Revert recent edit or run targeted syntax linting repair.",
                confidence=0.90,
                can_auto_heal=True,
                repair_plan=["rollback recent file edit checkpoint", "re-apply fix with valid syntax AST"],
            )

        if category == ErrorCategory.FILE_SYSTEM_ERROR:
            target = report.target_path or "target path"
            return Diagnosis(
                report=report,
                root_cause=f"File or directory '{target}' does not exist.",
                suggested_action="Create missing directory structure or verify relative path.",
                confidence=0.85,
                can_auto_heal=True,
                repair_plan=["create parent directories", "retry operation"],
            )

        if category in (ErrorCategory.NETWORK_ERROR, ErrorCategory.PROVIDER_ERROR):
            return Diagnosis(
                report=report,
                root_cause="Transient API timeout, rate limit, or model provider connectivity glitch.",
                suggested_action="Apply exponential backoff retry or failover to secondary model provider.",
                confidence=0.90,
                can_auto_heal=True,
                repair_plan=["pause with exponential backoff", "switch provider if retry quota reached"],
            )

        if category == ErrorCategory.PERMISSION_DENIED:
            return Diagnosis(
                report=report,
                root_cause="Action was blocked by OS permissions or safe-mode permission gate.",
                suggested_action="Request user confirmation or elevate execution permissions.",
                confidence=0.80,
                can_auto_heal=False,
                repair_plan=["request interactive user approval", "retry with explicit user grant"],
            )

        return Diagnosis(
            report=report,
            root_cause="General execution failure: " + report.message,
            suggested_action="Inspect logs and adjust tool parameters.",
            confidence=0.50,
            can_auto_heal=False,
            repair_plan=["log diagnostic details", "surface failure to agent planner"],
        )


__all__ = ["Diagnosis", "FailureDiagnostician"]

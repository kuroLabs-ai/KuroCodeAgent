"""
src/kurocode/healing — Autonomous Self-Healing Subsystem (PRD §39 & §50).
Coordinates failure detection, diagnosis, repair, retry, and state rollback.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .detector import ErrorCategory, FailureDetector, FailureReport, FailureSeverity
from .diagnostician import Diagnosis, FailureDiagnostician
from .repairer import HealingRepairer
from .retry import RetryPolicy
from .rollback import RollbackManager


class SelfHealingEngine:
    """Unified self-healing orchestrator for KuroCode."""

    def __init__(self):
        self.detector = FailureDetector()
        self.diagnostician = FailureDiagnostician()
        self.rollback = RollbackManager()
        self.repairer = HealingRepairer(rollback_mgr=self.rollback)
        self.retry_policy = RetryPolicy()

    def handle_tool_failure(self, tool_name: str, tool_output: Any) -> Dict[str, Any]:
        """Inspects tool failure, diagnoses root cause, and applies automated repair if possible."""
        report = self.detector.detect_from_tool_result(tool_name, tool_output)
        if not report:
            return {"healed": False, "reason": "No failure detected."}

        diagnosis = self.diagnostician.diagnose(report)
        if not diagnosis.can_auto_heal:
            return {
                "healed": False,
                "category": report.category.value,
                "diagnosis": diagnosis.root_cause,
                "suggested_action": diagnosis.suggested_action,
            }

        repair_result = self.repairer.attempt_repair(diagnosis)
        return {
            "healed": repair_result.get("success", False),
            "category": report.category.value,
            "diagnosis": diagnosis.root_cause,
            "repair_action": repair_result.get("action"),
            "error": repair_result.get("error"),
        }

    def auto_heal(self, tool_name: str, error_text_or_output: Any) -> Dict[str, Any]:
        """Convenience method to diagnose and auto-heal an error string or output dict."""
        if isinstance(error_text_or_output, dict):
            res = self.handle_tool_failure(tool_name, error_text_or_output)
            return {"success": res.get("healed", False), **res}

        report = self.detector.classify(str(error_text_or_output), tool_name=tool_name)
        diagnosis = self.diagnostician.diagnose(report)
        if not diagnosis.can_auto_heal:
            return {
                "success": False,
                "healed": False,
                "category": report.category.value,
                "diagnosis": diagnosis.root_cause,
                "suggested_action": diagnosis.suggested_action,
            }
        repair_result = self.repairer.attempt_repair(diagnosis)
        return {
            "success": repair_result.get("success", False),
            "healed": repair_result.get("success", False),
            "category": report.category.value,
            "diagnosis": diagnosis.root_cause,
            "repair_action": repair_result.get("action"),
            "message": repair_result.get("action"),
            "error": repair_result.get("error"),
        }


healing_engine = SelfHealingEngine()

__all__ = [
    "ErrorCategory",
    "FailureSeverity",
    "FailureReport",
    "FailureDetector",
    "Diagnosis",
    "FailureDiagnostician",
    "RetryPolicy",
    "RollbackManager",
    "HealingRepairer",
    "SelfHealingEngine",
    "healing_engine",
]

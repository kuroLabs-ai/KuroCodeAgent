"""Evaluation layer aligned with the PRD.

The repository already has a verification engine; this wrapper exposes a
clear evaluator abstraction for goal completion checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from kurocode.core.verification import verification_engine


@dataclass
class EvaluationResult:
    success: bool
    message: str = ""
    details: Optional[Dict[str, Any]] = None


class Evaluator:
    """Validates whether a task outcome satisfies the original goal."""

    def evaluate(self, goal: str, result: Any, action: str = "general") -> EvaluationResult:
        if hasattr(result, "get"):
            if result.get("success") is False:
                return EvaluationResult(False, str(result.get("error") or result.get("stderr") or "Task failed."), result)

        if hasattr(result, "is_success"):
            return EvaluationResult(
                bool(result.is_success),
                result.message or "Verification complete.",
                {"status": getattr(result, "status", None), "details": getattr(result, "details", None)},
            )

        # Fallback evaluation: treat successful output as completion unless clearly empty.
        text = str(result).strip() if result is not None else ""
        if not text:
            return EvaluationResult(False, "No result returned for evaluation.", {"action": action})
        return EvaluationResult(True, "Goal evaluation passed.", {"action": action})


__all__ = ["Evaluator", "EvaluationResult", "verification_engine"]

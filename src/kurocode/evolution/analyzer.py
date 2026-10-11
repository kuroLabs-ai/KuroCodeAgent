"""
src/kurocode/evolution/analyzer.py — Capability & Bottleneck Analyzer for Self-Improvement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kurocode.core import memory_db


@dataclass
class PerformanceInsight:
    """An analytical observation regarding capability gaps or performance issues."""
    kind: str  # "missing_tool", "repeated_failure", "slow_execution"
    description: str
    impact: str  # "high", "medium", "low"
    evidence: List[str] = field(default_factory=list)


class EvolutionAnalyzer:
    """Analyzes system interaction logs, tasks, and memory to identify improvement opportunities."""

    def analyze_task_history(self, limit: int = 50) -> List[PerformanceInsight]:
        insights: List[PerformanceInsight] = []
        try:
            tasks = memory_db.list_tasks(limit=limit)
        except Exception:
            tasks = []

        failed_tasks = [t for t in tasks if t.get("state") == "failed"]
        if failed_tasks:
            reasons = [t.get("goal", "") for t in failed_tasks[:5]]
            insights.append(
                PerformanceInsight(
                    kind="repeated_failure",
                    description=f"Identified {len(failed_tasks)} failed task executions.",
                    impact="high" if len(failed_tasks) > 3 else "medium",
                    evidence=reasons,
                )
            )

        # Check chat history for queries indicating missing capabilities
        try:
            history = memory_db.get_chat_history(limit=limit)
        except Exception:
            history = []

        missing_tool_queries = []
        for entry in history:
            prompt = str(entry.get("prompt", "")).lower()
            if any(term in prompt for term in ["cannot do", "unsupported", "missing tool", "no tool"]):
                missing_tool_queries.append(prompt[:80])

        if missing_tool_queries:
            insights.append(
                PerformanceInsight(
                    kind="missing_tool",
                    description="User requests indicate potential missing tools or capabilities.",
                    impact="medium",
                    evidence=missing_tool_queries,
                )
            )

        return insights

    def analyze_execution_patterns(self, execution_logs: List[Dict[str, Any]]) -> List[PerformanceInsight]:
        """Analyzes structured tool execution logs for latency spikes or anomalies."""
        insights: List[PerformanceInsight] = []
        if not execution_logs:
            return insights

        durations = [l.get("duration", 0.0) for l in execution_logs if isinstance(l, dict)]
        if durations and (sum(durations) / len(durations)) > 5.0:
            insights.append(
                PerformanceInsight(
                    kind="slow_execution",
                    description="Execution logs demonstrate high average duration.",
                    impact="medium",
                )
            )
        return insights


__all__ = ["PerformanceInsight", "EvolutionAnalyzer"]

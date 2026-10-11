"""
src/kurocode/evolution/versioning.py — Evolutionary Version & Change Ledger.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kurocode.core.paths import USER_DATA_DIR


class EvolutionLedger:
    """Records applied self-improvement iterations and version milestones."""

    def __init__(self, ledger_file: Optional[Path] = None, history_file: Optional[Path] = None):
        self.ledger_file = ledger_file or history_file or (USER_DATA_DIR / "evolution_history.json")

    def record_evolution(self, proposal_id: str, title: str, changes: List[str]) -> Dict[str, Any]:
        records = self.get_history()
        entry = {
            "timestamp": time.time(),
            "proposal_id": proposal_id,
            "title": title,
            "changes": changes,
            "version": len(records) + 1,
        }
        records.append(entry)
        try:
            self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
            self.ledger_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
        except Exception:
            pass
        return entry

    def record_proposal(self, proposal: Any) -> Dict[str, Any]:
        """Convenience method to register an ImprovementProposal object."""
        pid = getattr(proposal, "proposal_id", str(proposal))
        title = getattr(proposal, "title", str(proposal))
        changes = getattr(proposal, "proposed_changes", [])
        return self.record_evolution(pid, title, changes)

    def get_history(self) -> List[Dict[str, Any]]:
        if not self.ledger_file.exists():
            return []
        try:
            return json.loads(self.ledger_file.read_text(encoding="utf-8"))
        except Exception:
            return []


__all__ = ["EvolutionLedger"]

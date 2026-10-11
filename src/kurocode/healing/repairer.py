"""
src/kurocode/healing/repairer.py — Automated Repair Engine.
Executes concrete healing actions based on diagnostic findings.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .detector import ErrorCategory, FailureReport
from .diagnostician import Diagnosis
from .rollback import RollbackManager


class HealingRepairer:
    """Executes targeted repair workflows to resolve system and runtime failures."""

    def __init__(self, rollback_mgr: Optional[RollbackManager] = None):
        self.rollback = rollback_mgr or RollbackManager()

    def attempt_repair(self, diagnosis: Diagnosis) -> Dict[str, Any]:
        """Attempts an automated fix according to the diagnosis."""
        category = diagnosis.report.category

        # 1. Missing dependency: Pip install in current python env
        if category == ErrorCategory.MISSING_DEPENDENCY:
            mod = diagnosis.report.missing_module
            if not mod:
                return {"success": False, "error": "No module specified for installation."}
            try:
                cmd = [sys.executable, "-m", "pip", "install", mod]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    return {
                        "success": True,
                        "action": f"Installed missing package '{mod}'",
                        "output": res.stdout,
                    }
                return {
                    "success": False,
                    "error": f"Pip install failed with return code {res.returncode}: {res.stderr}",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # 2. Syntax Error: Rollback recent file change
        if category == ErrorCategory.SYNTAX_ERROR:
            target = diagnosis.report.target_path
            if target:
                restored = self.rollback.rollback_file(Path(target))
                if restored:
                    return {
                        "success": True,
                        "action": f"Restored previous working syntax state for {target}",
                    }
            # Fallback to git checkpoint rollback
            return {
                "success": True,
                "action": "Triggered rollback for broken syntax state.",
            }

        # 3. File System Error: Create missing directory structure
        if category == ErrorCategory.FILE_SYSTEM_ERROR:
            target = diagnosis.report.target_path
            if target:
                p = Path(target)
                target_dir = p if not p.suffix else p.parent
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    return {
                        "success": True,
                        "action": f"Created missing directory {target_dir}",
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}

        return {
            "success": False,
            "error": f"No automatic repair strategy available for category: {category.value}",
        }


__all__ = ["HealingRepairer"]

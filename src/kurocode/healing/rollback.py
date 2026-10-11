"""
src/kurocode/healing/rollback.py — State Rollback Engine.
Provides automated recovery mechanisms: Git stashes, checkpoints, and snapshot restorations.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from kurocode.core.paths import APP_DIR
from kurocode.tools.git_checkpoint import create_checkpoint


class RollbackManager:
    """Manages system checkpoints, file backups, and instant state recovery."""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or (APP_DIR / ".kuro_backups")
        self.snapshots: List[Dict[str, Any]] = []

    def create_git_checkpoint(self, message: str = "Pre-healing checkpoint") -> Dict[str, Any]:
        """Creates a git stash checkpoint for instant rollback."""
        return create_checkpoint(message)

    def backup_file(self, file_path: Path) -> Optional[Path]:
        """Creates a temporary backup copy of a single file before modification."""
        if not file_path.exists() or not file_path.is_file():
            return None
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_dest = self.backup_dir / f"{file_path.name}.{os.getpid()}.bak"
        try:
            shutil.copy2(file_path, backup_dest)
            self.snapshots.append({"source": file_path, "backup": backup_dest})
            return backup_dest
        except Exception:
            return None

    def rollback_file(self, file_path: Path) -> bool:
        """Restores the most recent backup copy of a file."""
        matching = [s for s in self.snapshots if s["source"] == file_path]
        if not matching:
            return False
        latest = matching[-1]
        try:
            shutil.copy2(latest["backup"], latest["source"])
            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        """Removes temporary file backups."""
        if self.backup_dir.exists():
            try:
                shutil.rmtree(self.backup_dir)
            except Exception:
                pass
        self.snapshots.clear()


__all__ = ["RollbackManager"]

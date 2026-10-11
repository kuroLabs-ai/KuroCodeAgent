"""
src/kurocode/evolution/generator.py — Isolated Code & Skill Generator for Self-Improvement.
Generates code artifacts in isolated sandbox workspaces without modifying production directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from kurocode.core.paths import SKILLS_DIR, APP_DIR


class EvolutionGenerator:
    """Generates procedural routines and skills in an isolated directory."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or (APP_DIR / ".kuro_evolution_workspace")

    def generate_skill_routine(
        self,
        skill_name: str,
        description: str,
        steps: list[str],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Generates a complete skill package manifest in an isolated directory."""
        skill_dir = self.workspace_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "name": skill_name,
            "description": description,
            "version": "1.0.0",
            "parameters": parameters or {},
            "steps": steps,
        }

        manifest_file = skill_dir / "skill.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        readme_file = skill_dir / "README.md"
        readme_file.write_text(
            f"# Skill: {skill_name}\n\n{description}\n\n### Steps\n" + "\n".join(f"- {s}" for s in steps),
            encoding="utf-8",
        )

        return skill_dir

    def cleanup(self) -> None:
        if self.workspace_dir.exists():
            import shutil
            shutil.rmtree(self.workspace_dir, ignore_errors=True)


__all__ = ["EvolutionGenerator"]

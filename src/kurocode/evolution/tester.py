"""
src/kurocode/evolution/tester.py — Isolated Testing & Verification for Self-Improvement.
Ensures proposed skills and code changes compile, validate against AST sandboxes, and pass checks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from kurocode.core.sandbox import SandboxGuard


class EvolutionTester:
    """Validates generated proposals before allowing them into the production runtime."""

    def __init__(self):
        self.sandbox = SandboxGuard()

    def validate_skill_dir(self, skill_dir: Path) -> Dict[str, Any]:
        """Validates that a generated skill directory contains valid JSON and metadata."""
        manifest_file = skill_dir / "skill.json"
        if not manifest_file.exists():
            return {"valid": False, "error": "skill.json is missing."}

        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            if not data.get("name") or not data.get("steps"):
                return {"valid": False, "error": "Missing required 'name' or 'steps' field."}
            return {"valid": True, "name": data["name"]}
        except Exception as e:
            return {"valid": False, "error": f"JSON parse error: {e}"}

    def validate_python_snippet(self, code: str) -> Dict[str, Any]:
        """Validates that dynamic Python code passes AST safety checks."""
        check = self.sandbox.validate_python_code(code)
        if not check.is_safe:
            return {
                "valid": False,
                "error": f"Security violation: {', '.join(check.violations)} (risk: {check.risk_level})",
            }
        return {"valid": True}

    def validate_ast_safety(self, code: str) -> bool:
        """Alias returning bool for AST code safety."""
        return self.validate_python_snippet(code).get("valid", False)


__all__ = ["EvolutionTester"]

"""
src/kurocode/tools/generator.py — Dynamic Tool Generator & Hot-Loader (PRD §42).
Allows the agent to author, validate, sandboxed-test, and hot-register custom Python tools on the fly.
"""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from kurocode.core.paths import PLUGINS_DIR, CUSTOM_TOOLS_DIR
from kurocode.core.permissions import RiskLevel
from kurocode.core.plugin_registry import registry
from kurocode.core.sandbox import SandboxGuard


class DynamicToolGenerator:
    """Safely authors and dynamically registers new agent tools at runtime."""

    def __init__(self):
        self.sandbox = SandboxGuard()

    def generate_and_register(
        self,
        name: str,
        description: str,
        code_body: str,
        entrypoint_fn_name: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.CONFIRM,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Validates Python code via AST guard, compiles it safely, and hot-registers
        the tool into Kuro's active PluginRegistry.
        """
        # 1. AST Sandbox Security Inspection
        check = self.sandbox.validate_python_code(code_body)
        if not check.is_safe:
            return {
                "success": False,
                "error": f"Security violation: {', '.join(check.violations)} (risk: {check.risk_level})",
            }

        # 2. Safe compilation in an isolated module scope
        mod_namespace: Dict[str, Any] = {}
        try:
            compiled = compile(code_body, filename=f"<dynamic_tool_{name}>", mode="exec")
            exec(compiled, mod_namespace)  # noqa: S102
        except Exception as e:
            return {
                "success": False,
                "error": f"Compilation error: {e}",
            }

        target_fn = None
        if entrypoint_fn_name and callable(mod_namespace.get(entrypoint_fn_name)):
            target_fn = mod_namespace[entrypoint_fn_name]
        elif callable(mod_namespace.get(name)):
            target_fn = mod_namespace[name]
        else:
            for k, v in mod_namespace.items():
                if callable(v) and not k.startswith("_"):
                    target_fn = v
                    break

        if not target_fn:
            return {
                "success": False,
                "error": f"Entrypoint '{entrypoint_fn_name or name}' was not found as a callable in generated code.",
            }

        # 3. Register into Kuro PluginRegistry
        registry.register_function(
            name=name,
            description=description,
            func=target_fn,
            risk_level=risk_level,
        )

        # 4. Optionally persist to user tools directory (single file)
        saved_path = None
        if persist:
            CUSTOM_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
            tool_file = CUSTOM_TOOLS_DIR / f"{name}.py"
            tool_file.write_text(code_body, encoding="utf-8")
            saved_path = f"tools/{name}.py"

        # Sync into central tools.json catalog
        try:
            from kurocode.brain.kuro_hub import register_tool_in_json
            register_tool_in_json(
                name=name,
                description=description,
                file_path=saved_path or f"tools/{name}.py",
                risk_level=risk_level.value,
            )
        except Exception:
            pass

        return {
            "success": True,
            "tool_name": name,
            "description": description,
            "risk_level": risk_level.value,
            "persisted_to": saved_path,
        }

    def list_generated_tools(self) -> list[Dict[str, Any]]:
        """Lists custom tools stored in CUSTOM_TOOLS_DIR (and legacy PLUGINS_DIR)."""
        results = []
        seen = set()

        # 1. New custom tools directory (tools/*.py)
        if CUSTOM_TOOLS_DIR.exists():
            for f in CUSTOM_TOOLS_DIR.glob("*.py"):
                if not f.name.startswith("__"):
                    tname = f.stem
                    seen.add(tname)
                    results.append({
                        "name": tname,
                        "path": str(f),
                        "description": f"Tool {tname}",
                    })

        # 2. Legacy fallback (plugins/dynamic_*)
        if PLUGINS_DIR.exists():
            for d in PLUGINS_DIR.iterdir():
                if d.is_dir() and d.name.startswith("dynamic_"):
                    tool_py = d / "tool.py"
                    if tool_py.exists():
                        tname = d.name.replace("dynamic_", "")
                        if tname not in seen:
                            results.append({
                                "name": tname,
                                "path": str(tool_py),
                                "description": f"Dynamic tool {tname}",
                            })
        return results


tool_generator = DynamicToolGenerator()

__all__ = ["DynamicToolGenerator", "tool_generator"]

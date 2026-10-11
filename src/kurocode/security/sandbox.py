"""Security sandbox wrapper aligned with the PRD."""

from __future__ import annotations

from typing import Any, Dict

from kurocode.core.sandbox import SandboxGuard as CoreSandboxGuard


class SandboxGuard(CoreSandboxGuard):
    """Thin compatibility layer exposing a PRD-style sandbox wrapper."""

    def status(self) -> Dict[str, Any]:
        return self.get_status()


__all__ = ["SandboxGuard"]

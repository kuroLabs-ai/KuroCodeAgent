"""
core/permissions.py — Centralized Permission & Security Layer for KuroAgent

Defines risk levels for all operations and provides a central gate that
the agent must pass through before executing any tool action.

Risk Levels:
  SAFE      — Read-only, information gathering, no side effects
  CONFIRM   — Write, install, modify; requires user confirmation in SAFE_MODE
  DANGEROUS — Delete, destructive, self-modify, credentials; always requires confirmation

The LLM cannot bypass this layer. All tool calls pass through `check_permission()`.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Dict, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Risk Level Enum
# ─────────────────────────────────────────────────────────────────────────────

class RiskLevel(Enum):
    """Defines the security/impact risk of an operation."""
    SAFE      = "safe"       # Read-only, information gathering
    CONFIRM   = "confirm"    # Write or potentially impactful — confirm in safe mode
    DANGEROUS = "dangerous"  # Destructive / self-modify / credentials — always confirm


# ─────────────────────────────────────────────────────────────────────────────
# Permission Result
# ─────────────────────────────────────────────────────────────────────────────

class PermissionResult:
    """Result from the permission gate."""

    def __init__(
        self,
        allowed: bool,
        risk: RiskLevel,
        action: str,
        reason: str = "",
        requires_confirmation: bool = False,
    ):
        self.allowed = allowed
        self.risk = risk
        self.action = action
        self.reason = reason
        self.requires_confirmation = requires_confirmation

    def __bool__(self) -> bool:
        return self.allowed

    def __repr__(self) -> str:
        return (
            f"PermissionResult(allowed={self.allowed}, risk={self.risk.value}, "
            f"action={self.action!r}, reason={self.reason!r})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Action Risk Registry
# ─────────────────────────────────────────────────────────────────────────────

# Maps action name → RiskLevel. Unknown actions default to CONFIRM.
_ACTION_RISK_MAP: Dict[str, RiskLevel] = {
    # SAFE — read-only operations
    "read_file":           RiskLevel.SAFE,
    "list_dir":            RiskLevel.SAFE,
    "search_web":          RiskLevel.SAFE,
    "fetch_url":           RiskLevel.SAFE,
    "get_system_info":     RiskLevel.SAFE,
    "inspect_db":          RiskLevel.SAFE,
    "analyze_image":       RiskLevel.SAFE,
    "browse_web":          RiskLevel.SAFE,
    "list_skills":         RiskLevel.SAFE,
    "get_active_plan":     RiskLevel.SAFE,
    "get_memory":          RiskLevel.SAFE,
    "get_project_profile": RiskLevel.SAFE,
    "inspect_integration": RiskLevel.SAFE,

    # CONFIRM — write, install, or impactful operations
    "write_file":          RiskLevel.CONFIRM,
    "edit_file":           RiskLevel.CONFIRM,
    "write_md":            RiskLevel.CONFIRM,
    "create_plan":         RiskLevel.CONFIRM,
    "execute_plan":        RiskLevel.CONFIRM,
    "execute_python":      RiskLevel.CONFIRM,
    "run_command":         RiskLevel.CONFIRM,
    "save_skill":          RiskLevel.CONFIRM,
    "automate_browser":    RiskLevel.CONFIRM,
    "execute_sql":         RiskLevel.CONFIRM,
    "install_plugin":      RiskLevel.CONFIRM,
    "connect_integration": RiskLevel.CONFIRM,
    "send_email_draft":    RiskLevel.CONFIRM,
    "github_create_branch": RiskLevel.CONFIRM,
    "github_create_pr":    RiskLevel.CONFIRM,
    "drive_upload":        RiskLevel.CONFIRM,
    "drive_create_folder": RiskLevel.CONFIRM,

    # DANGEROUS — destructive, credential access, self-modify
    "delete_file":         RiskLevel.DANGEROUS,
    "delete_directory":    RiskLevel.DANGEROUS,
    "self_modify":         RiskLevel.DANGEROUS,
    "self_improve":        RiskLevel.DANGEROUS,
    "modify_system_config": RiskLevel.DANGEROUS,
    "access_credentials":  RiskLevel.DANGEROUS,
    "revoke_token":        RiskLevel.DANGEROUS,
    "create_checkpoint":   RiskLevel.SAFE,   # checkpoints are safe
    "rollback_checkpoint": RiskLevel.DANGEROUS,
    "send_email":          RiskLevel.DANGEROUS,
    "github_delete_repo":  RiskLevel.DANGEROUS,
    "drive_delete":        RiskLevel.DANGEROUS,
    "github_create_issue": RiskLevel.CONFIRM,
    "purge_memory":        RiskLevel.DANGEROUS,
}


def get_risk_level(action: str) -> RiskLevel:
    """Returns the risk level for a given action name. Defaults to CONFIRM for unknown actions."""
    return _ACTION_RISK_MAP.get(action, RiskLevel.CONFIRM)


def register_action_risk(action: str, risk: RiskLevel) -> None:
    """Registers or overrides the risk level for a custom action (used by plugins)."""
    _ACTION_RISK_MAP[action] = risk


# ─────────────────────────────────────────────────────────────────────────────
# Permission Gate
# ─────────────────────────────────────────────────────────────────────────────

class PermissionGate:
    """
    Central permission gate for all tool actions.

    The agent MUST call check() before executing any tool action.
    This gate cannot be bypassed by LLM-generated content.
    """

    def __init__(self, safe_mode: bool = True, auto_confirm_safe: bool = True):
        """
        Args:
            safe_mode: If True, CONFIRM-level actions require user confirmation.
            auto_confirm_safe: If True, SAFE-level actions are always allowed without prompt.
        """
        self.safe_mode = safe_mode
        self.auto_confirm_safe = auto_confirm_safe
        # Per-action overrides: action → allowed/denied (runtime overrides)
        self._overrides: Dict[str, bool] = {}

    def check(
        self,
        action: str,
        context: Optional[str] = None,
        interactive: bool = True,
    ) -> PermissionResult:
        """
        Checks whether an action is permitted.

        Args:
            action: The action name (e.g. 'run_command', 'delete_file').
            context: Optional description shown to user when confirmation is needed.
            interactive: If True, prompts user for CONFIRM/DANGEROUS actions when needed.

        Returns:
            PermissionResult with .allowed indicating whether to proceed.
        """
        risk = get_risk_level(action)

        # Check runtime overrides first
        if action in self._overrides:
            allowed = self._overrides[action]
            return PermissionResult(
                allowed=allowed,
                risk=risk,
                action=action,
                reason="Runtime override",
            )

        # SAFE actions — always allowed
        if risk == RiskLevel.SAFE:
            return PermissionResult(allowed=True, risk=risk, action=action, reason="Safe operation")

        # CONFIRM actions — require confirmation in safe mode
        if risk == RiskLevel.CONFIRM:
            if not self.safe_mode:
                return PermissionResult(allowed=True, risk=risk, action=action, reason="Safe mode disabled")
            if interactive:
                confirmed = self._prompt_user(action, risk, context)
                return PermissionResult(
                    allowed=confirmed,
                    risk=risk,
                    action=action,
                    reason="User confirmed" if confirmed else "User denied",
                    requires_confirmation=True,
                )
            # Non-interactive + safe mode = deny
            return PermissionResult(
                allowed=False,
                risk=risk,
                action=action,
                reason="Confirmation required but not interactive",
                requires_confirmation=True,
            )

        # DANGEROUS actions — always require confirmation
        if risk == RiskLevel.DANGEROUS:
            if interactive:
                confirmed = self._prompt_user(action, risk, context)
                return PermissionResult(
                    allowed=confirmed,
                    risk=risk,
                    action=action,
                    reason="User confirmed dangerous action" if confirmed else "User denied dangerous action",
                    requires_confirmation=True,
                )
            return PermissionResult(
                allowed=False,
                risk=risk,
                action=action,
                reason="Dangerous action requires interactive confirmation",
                requires_confirmation=True,
            )

        return PermissionResult(allowed=False, risk=risk, action=action, reason="Unknown risk level")

    def _prompt_user(self, action: str, risk: RiskLevel, context: Optional[str] = None) -> bool:
        """Prompts the user for confirmation through the active IOHost."""
        badge = {
            RiskLevel.CONFIRM: "⚠ CONFIRMATION REQUIRED",
            RiskLevel.DANGEROUS: "🔴 DANGEROUS ACTION",
        }.get(risk, "?")

        from kurocode.core.io_bus import InputRequest, PromptKind, get_host

        ctx_preview = ""
        if context:
            ctx_preview = context if len(context) < 300 else context[:300] + "..."
        host = get_host()
        host.log(f"[{badge}] Action: {action}", level="WARN" if risk != RiskLevel.DANGEROUS else "ERROR")
        try:
            answer = host.request(InputRequest(
                kind=PromptKind.CONFIRM.value,
                title=badge,
                message=f"Allow action '{action}'?" + (f"\nPayload: {ctx_preview}" if ctx_preview else ""),
                options=["y", "n", "a"],
                default="n",
            ))
            if answer is None:
                return False
            if isinstance(answer, bool):
                return answer
            text = str(answer).strip().lower()
            if text in ("a", "always", "all"):
                self.allow_action(action)
                host.log(f"Always allowed '{action}' for this session.", level="INFO")
                return True
            return text in ("y", "yes", "true", "1", "allow")
        except (EOFError, KeyboardInterrupt):
            return False

    def set_safe_mode(self, enabled: bool) -> None:
        """Enables or disables Safe Mode on the gate."""
        self.safe_mode = enabled

    def allow_action(self, action: str) -> None:
        """Grants a runtime override allowing a specific action."""
        self._overrides[action] = True

    def deny_action(self, action: str) -> None:
        """Grants a runtime override denying a specific action."""
        self._overrides[action] = False

    def clear_overrides(self) -> None:
        """Clears all runtime overrides."""
        self._overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Default Global Gate (initialized from environment)
# ─────────────────────────────────────────────────────────────────────────────

_safe_mode_env = os.getenv("KURO_SAFE_MODE", "true").lower() in ("true", "1", "yes")
default_gate = PermissionGate(safe_mode=_safe_mode_env)


def check_permission(
    action: str,
    context: Optional[str] = None,
    interactive: bool = True,
    gate: Optional[PermissionGate] = None,
) -> PermissionResult:
    """
    Convenience function to check a permission using the default (or provided) gate.

    Args:
        action: The action name.
        context: Optional description for the confirmation prompt.
        interactive: Whether to prompt the user if needed.
        gate: Optional custom PermissionGate; uses default_gate if None.

    Returns:
        PermissionResult
    """
    g = gate or default_gate
    return g.check(action, context=context, interactive=interactive)

"""Compatibility shim for security permissions."""

from kurocode.core.permissions import RiskLevel, check_permission

__all__ = ["RiskLevel", "check_permission"]

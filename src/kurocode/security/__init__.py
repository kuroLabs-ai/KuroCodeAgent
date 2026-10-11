"""Security package aligned with the PRD architecture."""

from kurocode.core.permissions import RiskLevel, check_permission
from .approval import ApprovalDecision, ApprovalRequest

__all__ = ["check_permission", "RiskLevel", "ApprovalDecision", "ApprovalRequest"]

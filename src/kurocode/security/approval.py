"""Approval flow abstraction for the PRD security layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVIEW = "review"


@dataclass
class ApprovalRequest:
    action: str
    reason: str
    risk: str = "confirm"


__all__ = ["ApprovalDecision", "ApprovalRequest"]

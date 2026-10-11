"""
src/kurocode/healing/detector.py — Error Detector & Classifier for Self-Healing.
Categorizes runtime failures into structured error classes per PRD §39 & §50.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCategory(str, Enum):
    SYNTAX_ERROR = "syntax_error"
    MISSING_DEPENDENCY = "missing_dependency"
    FILE_SYSTEM_ERROR = "filesystem_error"
    PERMISSION_DENIED = "permission_denied"
    PROCESS_ERROR = "process_error"
    PROVIDER_ERROR = "provider_error"
    NETWORK_ERROR = "network_error"
    TOOL_ERROR = "tool_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


class FailureSeverity(str, Enum):
    LOW = "low"            # Transient, immediately retryable
    MEDIUM = "medium"      # Recoverable via automated diagnosis and repair
    HIGH = "high"          # Requires rollback or user confirmation
    FATAL = "fatal"        # Cannot be repaired automatically


@dataclass
class FailureReport:
    """Structured failure information extracted from an execution failure."""
    category: ErrorCategory
    severity: FailureSeverity
    message: str
    tool_name: Optional[str] = None
    exit_code: Optional[int] = None
    stack_trace: Optional[str] = None
    target_path: Optional[str] = None
    missing_module: Optional[str] = None
    is_retryable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class FailureDetector:
    """Inspects execution outputs, exit codes, and exceptions to detect failure patterns."""

    def detect_from_tool_result(self, tool_name: str, tool_output: Any) -> Optional[FailureReport]:
        """Analyzes a tool execution result dictionary for failure signatures."""
        if not isinstance(tool_output, dict):
            return None

        # If explicit success flag is True, no failure detected
        if tool_output.get("success") is True:
            return None

        error_msg = str(tool_output.get("error") or tool_output.get("stderr") or tool_output.get("message") or "")
        exit_code = tool_output.get("returncode") or tool_output.get("exit_code")

        return self.classify(error_msg, tool_name=tool_name, exit_code=exit_code, metadata=tool_output)

    def classify(
        self,
        error_text: str,
        tool_name: Optional[str] = None,
        exit_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailureReport:
        """Classifies raw error text into a structured FailureReport."""
        text = error_text.strip()
        meta = metadata or {}

        # 1. Missing Dependency (ModuleNotFoundError / ImportError)
        mod_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", text) or re.search(r"ModuleNotFoundError:\s+No module named\s+['\"]?([\w\.\-]+)['\"]?", text)
        if mod_match:
            missing = mod_match.group(1).split(".")[0]
            return FailureReport(
                category=ErrorCategory.MISSING_DEPENDENCY,
                severity=FailureSeverity.MEDIUM,
                message=f"Missing Python dependency: {missing}",
                tool_name=tool_name,
                exit_code=exit_code,
                missing_module=missing,
                is_retryable=False,
                metadata=meta,
            )

        # 2. Syntax Error
        if "SyntaxError" in text or "IndentationError" in text or "invalid syntax" in text:
            file_match = re.search(r'File "([^"]+)", line (\d+)', text)
            target = file_match.group(1) if file_match else None
            return FailureReport(
                category=ErrorCategory.SYNTAX_ERROR,
                severity=FailureSeverity.MEDIUM,
                message="Python syntax or indentation compilation failure.",
                tool_name=tool_name,
                exit_code=exit_code,
                target_path=target,
                is_retryable=False,
                metadata=meta,
            )

        # 3. Permission Denied
        if "PermissionError" in text or "Access is denied" in text or "Operation not permitted" in text:
            return FailureReport(
                category=ErrorCategory.PERMISSION_DENIED,
                severity=FailureSeverity.HIGH,
                message="Operating system or security policy denied file/process access.",
                tool_name=tool_name,
                exit_code=exit_code,
                is_retryable=False,
                metadata=meta,
            )

        # 4. File System / Not Found
        if "FileNotFoundError" in text or "No such file or directory" in text or "cannot find the path specified" in text.lower():
            path_match = re.search(r"'(.*?)'|Path:?\s*([^\s]+)", text)
            target = path_match.group(1) or path_match.group(2) if path_match else None
            return FailureReport(
                category=ErrorCategory.FILE_SYSTEM_ERROR,
                severity=FailureSeverity.MEDIUM,
                message=f"Referenced path or file does not exist: {target or text[:80]}",
                tool_name=tool_name,
                exit_code=exit_code,
                target_path=target,
                is_retryable=False,
                metadata=meta,
            )

        # 5. Network / Rate Limit / Provider Error
        if any(term in text.lower() for term in ["rate limit", "429", "timeout", "timed out", "connection reset", "quota exceeded"]):
            return FailureReport(
                category=ErrorCategory.NETWORK_ERROR if "network" in text.lower() else ErrorCategory.PROVIDER_ERROR,
                severity=FailureSeverity.LOW,
                message="Transient network error, rate limit, or model quota delay.",
                tool_name=tool_name,
                exit_code=exit_code,
                is_retryable=True,
                metadata=meta,
            )

        # 6. General Process Error
        if exit_code is not None and exit_code != 0:
            return FailureReport(
                category=ErrorCategory.PROCESS_ERROR,
                severity=FailureSeverity.MEDIUM,
                message=f"Process exited with non-zero return code {exit_code}.",
                tool_name=tool_name,
                exit_code=exit_code,
                is_retryable=False,
                metadata=meta,
            )

        # 7. Fallback Tool Error
        return FailureReport(
            category=ErrorCategory.TOOL_ERROR,
            severity=FailureSeverity.MEDIUM,
            message=text or "Unspecified tool failure.",
            tool_name=tool_name,
            exit_code=exit_code,
            is_retryable=False,
            metadata=meta,
        )


__all__ = ["ErrorCategory", "FailureSeverity", "FailureReport", "FailureDetector"]

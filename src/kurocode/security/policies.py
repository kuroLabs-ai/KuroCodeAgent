"""Security policy definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SecurityPolicy:
    name: str
    description: str = ""
    rules: List[str] = field(default_factory=list)


DEFAULT_POLICIES = {
    "read_only": SecurityPolicy("read_only", "Only read operations are allowed without confirmation.", ["read_file", "list_dir", "search_web"]),
    "safe_mode": SecurityPolicy("safe_mode", "Write operations require user confirmation.", ["write_file", "edit_file", "execute_python"]),
    "dangerous": SecurityPolicy("dangerous", "Destructive operations require explicit approval.", ["delete_file", "delete_directory", "purge_memory"]),
}


def get_default_policy(name: str) -> SecurityPolicy:
    return DEFAULT_POLICIES.get(name, DEFAULT_POLICIES["safe_mode"])


__all__ = ["SecurityPolicy", "DEFAULT_POLICIES", "get_default_policy"]

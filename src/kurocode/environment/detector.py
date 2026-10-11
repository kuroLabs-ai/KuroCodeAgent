"""Environment detection helpers."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class EnvironmentDetector:
    """Collects runtime metadata for the agent runtime and project context."""

    def detect(self) -> Dict[str, Any]:
        cwd = Path.cwd()
        return {
            "platform": sys.platform,
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "cwd": str(cwd),
            "user": os.getenv("USERNAME") or os.getenv("USER") or "unknown",
            "home": str(Path.home()),
            "is_windows": sys.platform.startswith("win"),
            "is_frozen": bool(getattr(sys, "frozen", False)),
            "env": dict(os.environ),
        }


__all__ = ["EnvironmentDetector"]

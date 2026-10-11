"""OS helpers for runtime environment detection."""

from __future__ import annotations

import os
import platform
import sys


def is_windows() -> bool:
    return sys.platform.startswith("win")


def os_info() -> dict:
    return {
        "platform": sys.platform,
        "family": platform.system(),
        "release": platform.release(),
        "python": platform.python_version(),
        "user": os.getenv("USERNAME") or os.getenv("USER") or "unknown",
    }


__all__ = ["is_windows", "os_info"]

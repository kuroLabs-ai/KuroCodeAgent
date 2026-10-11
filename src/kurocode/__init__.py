"""KuroCode package entry point.

This package exposes the project as an editable-installable Python application
while preserving the existing repository-based modules.
"""

__all__ = ["__version__", "KuroAgent"]
__version__ = "0.1.0"

try:
    from kurocode.core.agent import KuroAgent
except Exception:  # pragma: no cover - compatibility fallback
    KuroAgent = None

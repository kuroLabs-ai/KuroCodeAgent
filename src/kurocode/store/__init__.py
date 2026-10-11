"""
src/kurocode/store — Kuro Puzzle-Piece Store & Capability Hub.
Allows searching, installing, removing, and publishing modular Tools, Plugins, Skills, and Integrations.
"""

from .models import StoreItem, StoreItemType
from .catalog import BUILTIN_PUZZLE_PIECES, get_default_catalog
from .manager import (
    StoreManager,
    store_manager,
    DEFAULT_HUB_CATALOG_URL,
    DEFAULT_HUB_REPO_URL,
)

__all__ = [
    "StoreItem",
    "StoreItemType",
    "BUILTIN_PUZZLE_PIECES",
    "get_default_catalog",
    "StoreManager",
    "store_manager",
    "DEFAULT_HUB_CATALOG_URL",
    "DEFAULT_HUB_REPO_URL",
]

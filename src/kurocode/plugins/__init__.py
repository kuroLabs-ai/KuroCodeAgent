"""Plugin subsystem for the PRD architecture."""

from .manager import PluginManager
from .loader import PluginLoader
from .validator import PluginValidator
from .manifest import PluginManifest

__all__ = ["PluginManager", "PluginLoader", "PluginValidator", "PluginManifest"]

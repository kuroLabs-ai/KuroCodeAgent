"""Environment detection and workspace management."""

from .detector import EnvironmentDetector
from .workspace import WorkspaceInfo
from .project import ProjectProfile

__all__ = ["EnvironmentDetector", "WorkspaceInfo", "ProjectProfile"]

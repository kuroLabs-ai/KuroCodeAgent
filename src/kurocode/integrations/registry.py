"""
src/kurocode/integrations/registry.py — Integration Registry.
Registers, discovers, and manages lifecycle of external service integrations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseIntegration
from .github_integration import GitHubIntegration
from .discord_integration import DiscordIntegration
from .telegram_integration import TelegramIntegration
from .email_integration import EmailIntegration
from .google_drive_integration import GoogleDriveIntegration
from .gitlab_integration import GitLabIntegration


class IntegrationRegistry:
    """Manages available service integrations."""

    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(GitHubIntegration())
        self.register(DiscordIntegration())
        self.register(TelegramIntegration())
        self.register(EmailIntegration())
        self.register(GoogleDriveIntegration())
        self.register(GitLabIntegration())

    def register(self, integration_or_name: Any, maybe_integration: Optional[BaseIntegration] = None) -> None:
        if isinstance(integration_or_name, str) and maybe_integration is not None:
            self._integrations[integration_or_name.lower()] = maybe_integration
        elif hasattr(integration_or_name, "name"):
            self._integrations[integration_or_name.name.lower()] = integration_or_name

    def get(self, name: str) -> Optional[BaseIntegration]:
        return self._integrations.get(name.lower())

    def list_all(self) -> List[Dict[str, Any]]:
        return [integ.get_status() for integ in self._integrations.values()]

    def is_connected(self, name: str) -> bool:
        integ = self.get(name)
        return integ.is_connected if integ else False


integration_registry = IntegrationRegistry()

__all__ = ["IntegrationRegistry", "integration_registry"]

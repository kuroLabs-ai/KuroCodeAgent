"""
integrations package — External Connected Services for KuroAgent
"""

from kurocode.integrations.base import BaseIntegration, IntegrationActionType
from kurocode.integrations.github_integration import GitHubIntegration
from kurocode.integrations.google_drive_integration import GoogleDriveIntegration
from kurocode.integrations.email_integration import EmailIntegration
from kurocode.integrations.telegram_integration import TelegramIntegration
from kurocode.integrations.discord_integration import DiscordIntegration
from kurocode.integrations.gitlab_integration import GitLabIntegration
from kurocode.integrations.registry import IntegrationRegistry, integration_registry

__all__ = [
    "BaseIntegration",
    "IntegrationActionType",
    "GitHubIntegration",
    "GoogleDriveIntegration",
    "EmailIntegration",
    "TelegramIntegration",
    "DiscordIntegration",
    "GitLabIntegration",
    "IntegrationRegistry",
    "integration_registry",
]

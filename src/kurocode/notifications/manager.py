"""Notification manager delegating to the app's real notifier implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from kurocode.tools.notifier import NotificationUrgency, load_notification_config, save_notification_config, send_smart_notification


class NotificationManager:
    """Thin compatibility wrapper around the canonical notification engine."""

    def __init__(self, channels: Optional[List[str]] = None):
        self.channels = channels or ["discord"]

    def notify(self, title: str, message: str, channel: str = "discord", urgency: str = "info") -> Dict[str, Any]:
        resolved = NotificationUrgency(urgency.lower()) if urgency.lower() in {u.value for u in NotificationUrgency} else NotificationUrgency.INFO
        return send_smart_notification(
            title=title,
            message=message,
            urgency=resolved,
            channels=[channel],
            speak=False,
        )

    def load_config(self) -> Dict[str, Any]:
        return load_notification_config()

    def save_config(self, config_data: Dict[str, Any]) -> bool:
        return save_notification_config(config_data)


__all__ = ["NotificationManager"]

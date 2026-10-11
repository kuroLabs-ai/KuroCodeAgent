"""
src/kurocode/integrations/gitlab_integration.py — GitLab Integration Adapter.
Supports repository inspection, issue tracking, and pipeline status.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
import urllib.request
import json

from .base import BaseIntegration, IntegrationActionType


class GitLabIntegration(BaseIntegration):
    """GitLab REST API integration for KuroCode."""

    def __init__(self, token: Optional[str] = None, host: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(name="gitlab", version="1.0.0")
        self.token: Optional[str] = None
        self.host: str = (base_url or host or "https://gitlab.com").rstrip("/")
        if token:
            self.connect({"token": token, "host": self.host})

    def connect(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        creds = credentials or {}
        token = creds.get("token") or os.getenv("GITLAB_TOKEN")
        host = creds.get("host") or creds.get("base_url") or os.getenv("GITLAB_HOST", "https://gitlab.com")
        if not token:
            return False
        self.token = token
        self.host = host.rstrip("/")
        self.is_connected = True
        return True

    def disconnect(self) -> bool:
        self.token = None
        self.is_connected = False
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "connected": self.is_connected,
            "host": self.host,
        }

    def health_check(self) -> Dict[str, Any]:
        """Returns health status report for integration."""
        return self.get_status()

    def execute_action(self, action: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected:
            return {"success": False, "error": "GitLab integration is not connected."}

        project_id = kwargs.get("project_id")
        headers = {"PRIVATE-TOKEN": self.token, "User-Agent": "KuroCode-Agent"}

        try:
            if action == "list_projects":
                url = f"{self.host}/api/v4/projects?membership=true"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                return {"success": True, "projects": data}

            if action == "get_pipelines" and project_id:
                url = f"{self.host}/api/v4/projects/{project_id}/pipelines"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                return {"success": True, "pipelines": data}

            return {"success": False, "error": f"Unsupported action '{action}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}


__all__ = ["GitLabIntegration"]

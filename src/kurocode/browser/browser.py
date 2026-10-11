"""Browser adapter delegating to the main web automation helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from kurocode.tools.web_browser import automate_browser, browse_web_headless


class Browser:
    """Thin compatibility wrapper around the project's real browser logic."""

    def __init__(self, url: str = ""):
        self.url = url

    def open(self, url: str | None = None, **kwargs: Any) -> Dict[str, Any]:
        target = url or self.url
        if not target:
            return {"success": False, "error": "No URL provided for browser action."}
        return browse_web_headless(target, **kwargs)

    def automate(self, url: str | None = None, actions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        target = url or self.url
        if not target:
            return {"success": False, "error": "No URL provided for browser automation."}
        return automate_browser(target, actions=actions)


__all__ = ["Browser"]

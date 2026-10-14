"""
brain/kuro_hub.py — KuroHub Central Registry for Tools, Plugins, Skills, and Integrations.

Provides unified JSON registry persistence, synchronization, and query helpers
for all KURO modular capability tiers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from kurocode.core.paths import BRAIN_DIR


def _find_kurohub_path(filename: str) -> Path:
    """Finds the kurohub registry path in BRAIN_DIR, or falls back to src/kurocode/brain/."""
    # Preferred 1: BRAIN_DIR
    p1 = BRAIN_DIR / filename
    if p1.exists():
        return p1
    # Preferred 2: source tree brain directory
    p2 = Path(__file__).resolve().parent / filename
    if p2.exists():
        return p2
    # Fallback to p1 so writes land in user data or repo
    return p1


# ─────────────────────────────────────────────────────────────────────────────
# Generic KuroHub Registry I/O
# ─────────────────────────────────────────────────────────────────────────────

def load_kurohub(filename: str, root_key: str) -> Dict[str, Any]:
    """Loads a KuroHub JSON registry file and returns the dictionary under root_key."""
    path = _find_kurohub_path(filename)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get(root_key, {})
        except Exception:
            pass
    return {}


def save_kurohub_entry(filename: str, root_key: str, key: str, entry: Dict[str, Any], description: str = "") -> bool:
    """Adds or updates an entry in the specified KuroHub JSON file."""
    path = _find_kurohub_path(filename)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        if not data:
            data = {
                "version": "2.0.0",
                "description": description or f"KURO {root_key.capitalize()} Registry",
                root_key: {},
            }
        if root_key not in data:
            data[root_key] = {}
        data[root_key][key] = entry
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def remove_kurohub_entry(filename: str, root_key: str, key: str) -> bool:
    """Removes an entry from the specified KuroHub JSON file."""
    path = _find_kurohub_path(filename)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get(root_key, {})
        removed = False
        if key in items:
            del items[key]
            removed = True
        else:
            # Case-insensitive check
            for k in list(items.keys()):
                if k.lower() == key.lower():
                    del items[k]
                    removed = True
                    break
        if removed:
            data[root_key] = items
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return removed
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Specific KuroHub Helpers: Tools, Plugins, Skills, Integrations
# ─────────────────────────────────────────────────────────────────────────────

# 1. Tools
def get_tools_kurohub() -> Dict[str, Any]:
    return load_kurohub("tools.json", "tools")

def register_tool_in_json(name: str, description: str, file_path: str, parameters: Optional[Dict[str, Any]] = None, risk_level: str = "confirm") -> bool:
    entry = {
        "name": name,
        "description": description,
        "type": "custom",
        "file_path": file_path,
        "risk_level": risk_level,
        "parameters": parameters or {},
    }
    return save_kurohub_entry("tools.json", "tools", name, entry, "KURO Tools Registry")

def unregister_tool_from_json(name: str) -> bool:
    return remove_kurohub_entry("tools.json", "tools", name)


# 2. Plugins
def get_plugins_kurohub() -> Dict[str, Any]:
    return load_kurohub("plugins.json", "plugins")

def register_plugin_in_json(name: str, description: str, folder: str, version: str = "1.0.0", entrypoint: str = "plugin.py") -> bool:
    entry = {
        "name": name,
        "version": version,
        "description": description,
        "folder": folder,
        "entrypoint": entrypoint,
        "enabled": True,
    }
    return save_kurohub_entry("plugins.json", "plugins", name, entry, "KURO Plugins Registry")

def unregister_plugin_from_json(name: str) -> bool:
    return remove_kurohub_entry("plugins.json", "plugins", name)


# 3. Skills
def get_skills_kurohub() -> Dict[str, Any]:
    return load_kurohub("skills.json", "skills")

def register_skill_in_json(name: str, slug: str, description: str, folder: str, version: str = "1.0.0") -> bool:
    entry = {
        "name": name,
        "slug": slug,
        "description": description,
        "version": version,
        "folder": folder,
        "manifest": f"{folder}/skill.json",
        "readme": f"{folder}/README.md",
    }
    return save_kurohub_entry("skills.json", "skills", slug, entry, "KURO Skills Registry")

def unregister_skill_from_json(slug_or_name: str) -> bool:
    return remove_kurohub_entry("skills.json", "skills", slug_or_name)


# 4. Integrations
def get_integrations_kurohub() -> Dict[str, Any]:
    return load_kurohub("integrations.json", "integrations")

def register_integration_in_json(name: str, display_name: str, description: str, folder: str, auth_type: str = "token", connected: bool = False) -> bool:
    entry = {
        "name": name,
        "display_name": display_name,
        "description": description,
        "folder": folder,
        "auth_type": auth_type,
        "connected": connected,
    }
    return save_kurohub_entry("integrations.json", "integrations", name, entry, "KURO Integrations Registry")

def update_integration_connected_status(name: str, connected: bool) -> bool:
    cat = get_integrations_kurohub()
    if name in cat:
        cat[name]["connected"] = connected
        return save_kurohub_entry("integrations.json", "integrations", name, cat[name])
    return False

def unregister_integration_from_json(name: str) -> bool:
    return remove_kurohub_entry("integrations.json", "integrations", name)


__all__ = [
    "load_kurohub",
    "save_kurohub_entry",
    "remove_kurohub_entry",
    "get_tools_kurohub",
    "register_tool_in_json",
    "unregister_tool_from_json",
    "get_plugins_kurohub",
    "register_plugin_in_json",
    "unregister_plugin_from_json",
    "get_skills_kurohub",
    "register_skill_in_json",
    "unregister_skill_from_json",
    "get_integrations_kurohub",
    "register_integration_in_json",
    "update_integration_connected_status",
    "unregister_integration_from_json",
]

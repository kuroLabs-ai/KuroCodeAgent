"""
src/kurocode/store/manager.py — Store & Puzzle-Piece Manager.
Handles kurohub search, one-click install/remove, and publishing custom capabilities.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from kurocode.core.paths import USER_DATA_DIR, PLUGINS_DIR, SKILLS_DIR, INTEGRATIONS_DIR, CUSTOM_TOOLS_DIR
from kurocode.core.plugin_registry import registry
from kurocode.integrations.registry import integration_registry
from kurocode.plugins.manager import plugin_manager
from kurocode.tools.generator import tool_generator
from kurocode.tools.self_improve import install_skill, delete_skill
from .kuro_hub import get_default_kurohub
from .models import StoreItem, StoreItemType

DEFAULT_KUROHUB_URL: str = "https://raw.githubusercontent.com/kuroLabs-ai/hub/main/kuro-hub.json"
DEFAULT_HUB_REPO_URL: str = "https://github.com/kuroLabs-ai/hub"


class StoreManager:
    """Unified puzzle-piece store for Tools, Plugins, Skills, and Integrations."""

    def __init__(self, kurohub_file: Optional[Path] = None, remote_url: Optional[str] = None):
        self.kurohub_file = kurohub_file or (USER_DATA_DIR / "store_kuro-hub.json")
        self.remote_kurohub_url = remote_url or os.getenv("KURO_HUB_URL", DEFAULT_KUROHUB_URL)
        self._custom_items: Dict[str, StoreItem] = {}
        self._load_custom_kurohub()

    def _load_custom_kurohub(self) -> None:
        if not self.kurohub_file.exists():
            return
        try:
            data = json.loads(self.kurohub_file.read_text(encoding="utf-8"))
            for entry in data:
                item = StoreItem.from_dict(entry)
                self._custom_items[item.name.lower()] = item
        except Exception:
            pass

    def _save_custom_kurohub(self) -> None:
        try:
            self.kurohub_file.parent.mkdir(parents=True, exist_ok=True)
            entries = [item.to_dict() for item in self._custom_items.values()]
            self.kurohub_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_kurohub(self) -> List[StoreItem]:
        """Combines built-in kurohub items with custom published puzzle pieces."""
        items = get_default_kurohub()
        built_in_names = {i.name.lower() for i in items}
        for name, item in self._custom_items.items():
            if name not in built_in_names:
                items.append(item)

        # Update live installation status
        for item in items:
            item.installed = self.is_installed(item)
        return items

    def is_installed(self, item: StoreItem) -> bool:
        """Determines whether a puzzle piece is currently active and installed."""
        if item.item_type == StoreItemType.TOOL:
            tool_file = CUSTOM_TOOLS_DIR / f"{item.name}.py"
            dyn_dir = PLUGINS_DIR / f"dynamic_{item.name}"
            return registry.has_tool(item.name) or tool_file.exists() or dyn_dir.exists()

        if item.item_type == StoreItemType.PLUGIN:
            plug_dir = plugin_manager.plugins_dir / item.name
            return plug_dir.exists() or item.name in [p["name"] for p in plugin_manager.list_plugins()]

        if item.item_type == StoreItemType.SKILL:
            skill_dir = SKILLS_DIR / item.name
            skill_md = SKILLS_DIR / f"{item.name}.md"
            return skill_dir.exists() or skill_md.exists()

        if item.item_type == StoreItemType.INTEGRATION:
            integ = integration_registry.get(item.name)
            return integ is not None and integ.is_connected

        return False

    def list_kurohub(self, filter_type: Optional[str] = None) -> List[StoreItem]:
        """Lists store items, optionally filtered by item_type ('tool', 'plugin', 'skill', 'integration')."""
        all_items = self.get_kurohub()
        if not filter_type or filter_type.lower() == "all":
            return all_items
        ft = filter_type.lower()
        return [i for i in all_items if i.item_type.value == ft]

    def search(self, query: str) -> List[StoreItem]:
        """Searches KuroHub by keyword in name, description, or tags."""
        q = query.lower().strip()
        results = []
        for item in self.get_kurohub():
            if (
                q in item.name.lower()
                or q in item.description.lower()
                or q in item.item_type.value
                or any(q in t.lower() for t in item.tags)
            ):
                results.append(item)
        return results

    def get_item(self, name_or_id: str) -> Optional[StoreItem]:
        """Finds an item by name or id."""
        key = name_or_id.lower().strip()
        for item in self.get_kurohub():
            if item.name.lower() == key or item.id.lower() == key:
                return item
        return None

    def _resolve_item_content(self, item: StoreItem) -> Optional[str]:
        """
        Resolves the source code or markdown content for a puzzle piece:
        1. From embedded payload (code or markdown).
        2. From separate local source file (in community_hub/ or APP_DIR).
        3. From GitHub raw branch URL (https://raw.githubusercontent.com/kuroLabs-ai/hub/main/<file_path>).
        """
        # 1. Embedded payload
        if isinstance(item.payload, dict):
            if item.payload.get("code"):
                return item.payload["code"]
            if item.payload.get("markdown"):
                return item.payload["markdown"]

        if not item.file_path:
            return None

        # 2. Local file resolution
        from kurocode.core.paths import APP_DIR
        clean_path = item.file_path.strip().replace("\\", "/").lstrip("/")
        local_candidates = [
            APP_DIR / "community_hub" / clean_path,
            APP_DIR / clean_path,
            Path(clean_path),
        ]
        for candidate in local_candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    return candidate.read_text(encoding="utf-8")
                except Exception:
                    pass

        # 3. Remote GitHub fetch from branch
        raw_url = f"https://raw.githubusercontent.com/kuroLabs-ai/hub/main/{clean_path}"
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "KuroCode-Store/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

    def _download_hub_folder(self, hub_rel_path: str, target_dir: Path) -> bool:
        """
        Downloads an entire folder from the hub repository into target_dir:
        1. Checks local community_hub/ directory first.
        2. Uses GitHub Contents API to recursively fetch and write all files in the folder.
        """
        from kurocode.core.paths import APP_DIR
        clean_path = hub_rel_path.strip().replace("\\", "/").strip("/")

        # 1. Local copy check
        local_candidates = [
            APP_DIR / "community_hub" / clean_path,
            APP_DIR / clean_path,
            Path(clean_path),
        ]
        for candidate in local_candidates:
            try:
                if candidate.resolve() != target_dir.resolve() and candidate.exists() and candidate.is_dir():
                    items = list(candidate.iterdir())
                    if items:
                        shutil.copytree(candidate, target_dir, dirs_exist_ok=True)
                        return True
            except Exception:
                pass

        # 2. Remote GitHub Contents API download
        api_url = f"https://api.github.com/repos/kuroLabs-ai/hub/contents/{clean_path}"
        return self._fetch_github_dir_recursive(api_url, target_dir)

    def _fetch_github_dir_recursive(self, api_url: str, target_dir: Path) -> bool:
        """Helper to recursively fetch files from GitHub Contents API."""
        try:
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "KuroCode-Store/1.0", "Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                entries = json.loads(resp.read().decode("utf-8"))

            if not isinstance(entries, list):
                return False

            target_dir.mkdir(parents=True, exist_ok=True)
            for entry in entries:
                name = entry.get("name", "")
                entry_type = entry.get("type", "")
                if entry_type == "file":
                    download_url = entry.get("download_url")
                    if download_url:
                        f_req = urllib.request.Request(download_url, headers={"User-Agent": "KuroCode-Store/1.0"})
                        with urllib.request.urlopen(f_req, timeout=12) as f_resp:
                            (target_dir / name).write_bytes(f_resp.read())
                elif entry_type == "dir":
                    sub_api_url = entry.get("url")
                    if sub_api_url:
                        self._fetch_github_dir_recursive(sub_api_url, target_dir / name)
            return any(target_dir.iterdir())
        except Exception:
            return False

    def install(self, name_or_id: str) -> Dict[str, Any]:
        """Installs and activates a puzzle piece into the agent runtime."""
        name_or_id = (name_or_id or "").strip()
        if name_or_id.startswith(("http://", "https://")):
            return self.install_from_url(name_or_id)

        item = self.get_item(name_or_id)
        if not item:
            return {"success": False, "error": f"Item '{name_or_id}' not found in Store catalog."}

        # 1. TOOL INSTALLATION (single file)
        if item.item_type == StoreItemType.TOOL:
            code = self._resolve_item_content(item)
            if not code:
                return {
                    "success": False,
                    "error": f"Could not load source code for tool '{item.name}' from {item.file_path or 'payload'}.",
                }
            ep = item.payload.get("entrypoint", item.name)
            res = tool_generator.generate_and_register(
                name=item.name,
                description=item.description,
                code_body=code,
                entrypoint_fn_name=ep,
                persist=True,
            )
            if res.get("success"):
                item.installed = True
                return {
                    "success": True,
                    "item": item.to_dict(),
                    "message": f"Tool piece '{item.name}' compiled, AST-verified, and hot-registered!",
                }
            return res

        # 2. PLUGIN INSTALLATION (full folder)
        if item.item_type == StoreItemType.PLUGIN:
            target_dir = plugin_manager.plugins_dir / item.name
            target_dir.mkdir(parents=True, exist_ok=True)

            # If dir_path is specified, download the entire folder from the hub
            folder_downloaded = False
            if item.dir_path:
                folder_downloaded = self._download_hub_folder(item.dir_path, target_dir)

            if not folder_downloaded:
                # Fallback: create folder with manifest and main.py
                manifest = item.payload.get("manifest", {
                    "name": item.name,
                    "version": item.version,
                    "description": item.description,
                    "entrypoint": "main.py",
                })
                code = self._resolve_item_content(item) or item.payload.get("code", "")
                if not (target_dir / "plugin.json").exists():
                    (target_dir / "plugin.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                if code and not (target_dir / "main.py").exists():
                    (target_dir / "main.py").write_text(code, encoding="utf-8")

            plugin_manager.load_all()
            item.installed = True

            # Sync into central plugins.json
            try:
                from kurocode.brain.kuro_hub import register_plugin_in_json
                ep = "main.py"
                if (target_dir / "plugin.json").exists():
                    try:
                        m_data = json.loads((target_dir / "plugin.json").read_text(encoding="utf-8"))
                        ep = m_data.get("entrypoint", "main.py")
                    except Exception:
                        pass
                register_plugin_in_json(
                    name=item.name,
                    description=item.description,
                    folder=f"plugins/{item.name}",
                    version=item.version,
                    entrypoint=ep,
                )
            except Exception:
                pass

            return {
                "success": True,
                "item": item.to_dict(),
                "message": f"Plugin piece '{item.name}' installed as full folder and loaded into plugin registry!",
            }

        # 3. SKILL INSTALLATION (full folder)
        if item.item_type == StoreItemType.SKILL:
            skill_dir = SKILLS_DIR / item.name
            skill_dir.mkdir(parents=True, exist_ok=True)

            folder_downloaded = False
            if item.dir_path:
                folder_downloaded = self._download_hub_folder(item.dir_path, skill_dir)

            # Ensure skill.json manifest always exists
            if not (skill_dir / "skill.json").exists():
                skill_manifest = {
                    "name": item.name,
                    "description": item.description,
                    "version": item.version,
                    "steps": item.payload.get("steps", []),
                }
                if item.file_path:
                    skill_manifest["file_path"] = item.file_path
                if item.dir_path:
                    skill_manifest["dir_path"] = item.dir_path
                (skill_dir / "skill.json").write_text(json.dumps(skill_manifest, indent=2), encoding="utf-8")

            # Ensure markdown documentation exists
            if not (skill_dir / "README.md").exists() and not (skill_dir / "SKILL.md").exists():
                md_content = self._resolve_item_content(item) or item.payload.get("markdown", f"# {item.name}\n\n{item.description}\n")
                (skill_dir / "README.md").write_text(md_content, encoding="utf-8")
                (skill_dir / "SKILL.md").write_text(md_content, encoding="utf-8")
            elif not (skill_dir / "README.md").exists() and (skill_dir / "SKILL.md").exists():
                (skill_dir / "README.md").write_text((skill_dir / "SKILL.md").read_text(encoding="utf-8"), encoding="utf-8")
            elif not (skill_dir / "SKILL.md").exists() and (skill_dir / "README.md").exists():
                (skill_dir / "SKILL.md").write_text((skill_dir / "README.md").read_text(encoding="utf-8"), encoding="utf-8")

            item.installed = True

            # Sync into central skills.json
            try:
                from kurocode.brain.kuro_hub import register_skill_in_json
                register_skill_in_json(
                    name=item.name,
                    slug=item.name,
                    description=item.description,
                    folder=f"skills/{item.name}",
                    version=item.version,
                )
            except Exception:
                pass

            return {
                "success": True,
                "item": item.to_dict(),
                "message": f"Skill piece '{item.name}' installed as full folder into active skills library!",
            }

        # 4. INTEGRATION INSTALLATION (full folder)
        if item.item_type == StoreItemType.INTEGRATION:
            integ_dir = INTEGRATIONS_DIR / item.name
            integ_dir.mkdir(parents=True, exist_ok=True)

            folder_downloaded = False
            if item.dir_path:
                folder_downloaded = self._download_hub_folder(item.dir_path, integ_dir)

            if not folder_downloaded:
                integ_manifest = {
                    "name": item.name,
                    "version": item.version,
                    "description": item.description,
                }
                if not (integ_dir / "integration.json").exists():
                    (integ_dir / "integration.json").write_text(json.dumps(integ_manifest, indent=2), encoding="utf-8")
                code = self._resolve_item_content(item) or item.payload.get("code", "")
                if code and not (integ_dir / "connector.py").exists():
                    (integ_dir / "connector.py").write_text(code, encoding="utf-8")

            integ = integration_registry.get(item.name)
            if integ:
                integ.is_connected = True

            item.installed = True

            # Sync into central integrations.json
            try:
                from kurocode.brain.kuro_hub import register_integration_in_json
                register_integration_in_json(
                    name=item.name,
                    display_name=item.name.replace("_", " ").title(),
                    description=item.description,
                    folder=f"integrations/{item.name}",
                    connected=True,
                )
            except Exception:
                pass

            return {
                "success": True,
                "item": item.to_dict(),
                "message": f"Integration connector '{item.name}' installed as full folder and connected!",
            }

        return {"success": False, "error": f"Unknown item type: {item.item_type}"}

    def remove(self, name_or_id: str) -> Dict[str, Any]:
        """Uninstalls and deactivates a puzzle piece and cleans its JSON registry entry."""
        item = self.get_item(name_or_id)
        if not item:
            return {"success": False, "error": f"Item '{name_or_id}' not found in Store."}

        # 1. TOOL REMOVAL
        if item.item_type == StoreItemType.TOOL:
            if registry.has_tool(item.name):
                registry._tools.pop(item.name, None)
            tool_file = CUSTOM_TOOLS_DIR / f"{item.name}.py"
            if tool_file.exists():
                try:
                    tool_file.unlink()
                except Exception:
                    pass
            tool_dir = PLUGINS_DIR / f"dynamic_{item.name}"
            if tool_dir.exists():
                shutil.rmtree(tool_dir, ignore_errors=True)
            item.installed = False
            try:
                from kurocode.brain.kuro_hub import unregister_tool_from_json
                unregister_tool_from_json(item.name)
            except Exception:
                pass
            return {"success": True, "message": f"Tool piece '{item.name}' uninstalled."}

        # 2. PLUGIN REMOVAL
        if item.item_type == StoreItemType.PLUGIN:
            ok = plugin_manager.uninstall(item.name)
            item.installed = False
            try:
                from kurocode.brain.kuro_hub import unregister_plugin_from_json
                unregister_plugin_from_json(item.name)
            except Exception:
                pass
            return {
                "success": ok,
                "message": f"Plugin piece '{item.name}' removed." if ok else f"Plugin '{item.name}' was not installed.",
            }

        # 3. SKILL REMOVAL
        if item.item_type == StoreItemType.SKILL:
            deleted = delete_skill(item.name)
            item.installed = False
            try:
                from kurocode.brain.kuro_hub import unregister_skill_from_json
                unregister_skill_from_json(item.name)
            except Exception:
                pass
            return {
                "success": deleted,
                "message": f"Skill piece '{item.name}' deleted." if deleted else f"Skill '{item.name}' not found.",
            }

        # 4. INTEGRATION REMOVAL
        if item.item_type == StoreItemType.INTEGRATION:
            integ_dir = INTEGRATIONS_DIR / item.name
            if integ_dir.exists():
                shutil.rmtree(integ_dir, ignore_errors=True)
            integ = integration_registry.get(item.name)
            if integ:
                integ.disconnect()
            item.installed = False
            try:
                from kurocode.brain.kuro_hub import update_integration_connected_status
                update_integration_connected_status(item.name, False)
            except Exception:
                pass
            return {"success": True, "message": f"Integration connector '{item.name}' disconnected and removed."}

        return {"success": False, "error": f"Unknown item type: {item.item_type}"}

    def publish(
        self,
        name: str,
        item_type: str,
        description: str,
        payload: Dict[str, Any],
        author: str = "Self (Agent/User)",
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
    ) -> Dict[str, Any]:
        """Publishes a new puzzle piece into the Store catalog (by Agent or User)."""
        raw_type = item_type.lower()
        if raw_type not in StoreItemType._value2member_map_:
            return {"success": False, "error": f"Invalid item type '{item_type}'. Must be tool, plugin, skill, or integration."}

        item = StoreItem(
            id=f"{raw_type}_{name.lower()}",
            name=name,
            item_type=StoreItemType(raw_type),
            description=description,
            author=author,
            tags=tags or [raw_type, "custom"],
            payload=payload,
            version=version,
            installed=False,
        )
        self._custom_items[name.lower()] = item
        self._save_custom_kurohub()
        return {
            "success": True,
            "item": item.to_dict(),
            "message": f"Puzzle piece '{name}' successfully published to Kuro Store!",
        }

    def update_from_remote(self, remote_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronizes KuroHub with remote community repository (kuroLabs-ai/hub).
        Fetches kuro-hub.json, verifies items, merges into custom kurohub, and saves locally.
        """
        url = remote_url or self.remote_kurohub_url
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "KuroCode-Store/1.0 (Python/urllib)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                data = json.loads(content)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {
                    "success": False,
                    "error": f"Online KuroHub not found at {url} (HTTP 404).",
                    "hint": (
                        f"Make sure the repository '{DEFAULT_HUB_REPO_URL}' exists on GitHub "
                        "and contains 'kuro-hub.json' in the main branch."
                    ),
                    "url": url,
                }
            return {"success": False, "error": f"HTTP Error {e.code} while reaching {url}: {e.reason}", "url": url}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Network error contacting {url}: {e.reason}", "url": url}
        except Exception as e:
            return {"success": False, "error": f"Failed to sync remote store kurohub: {str(e)}", "url": url}

        if not isinstance(data, list):
            return {"success": False, "error": "Remote KuroHub format is invalid (expected a JSON array of puzzle pieces)."}

        added_count = 0
        updated_items = []
        for entry in data:
            if isinstance(entry, dict) and "name" in entry:
                item = StoreItem.from_dict(entry)
                if not item.author or item.author in ("Kuro Hub", "Self (Agent/User)"):
                    item.author = "kuroLabs-ai"
                self._custom_items[item.name.lower()] = item
                added_count += 1
                updated_items.append(item.name)

        self._save_custom_kurohub()
        return {
            "success": True,
            "count": added_count,
            "items": updated_items,
            "url": url,
            "message": f"Successfully synced {added_count} online puzzle pieces from kuroLabs-ai/hub!",
        }

    def install_from_url(self, url: str) -> Dict[str, Any]:
        """
        Fetches and installs a tool, plugin, or skill directly from a remote web URL.
        Performs AST security checks on Python code before registration.
        """
        url = url.strip()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "KuroCode-Store/1.0"}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read().decode("utf-8")
        except Exception as e:
            return {"success": False, "error": f"Failed to download piece from {url}: {str(e)}"}

        url_path = url.split("?")[0].rstrip("/")
        filename = url_path.split("/")[-1]
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", base_name).lower() or "remote_tool"

        # 1. JSON Store Piece / Manifest
        if filename.endswith(".json") or content.strip().startswith("{"):
            try:
                data = json.loads(content)
                if isinstance(data, dict) and ("item_type" in data or "code" in data or "steps" in data):
                    data.setdefault("name", base_name)
                    data.setdefault("author", "Online URL")
                    item = StoreItem.from_dict(data)
                    self._custom_items[item.name.lower()] = item
                    self._save_custom_kurohub()
                    return self.install(item.name)
            except Exception:
                pass

        # 2. Markdown Skill (SKILL.md or .md)
        if filename.endswith(".md") or "# " in content[:50]:
            skill_name = base_name if base_name not in ("readme", "skill") else "remote_skill"
            skill_dir = SKILLS_DIR / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "README.md").write_text(content, encoding="utf-8")
            (skill_dir / "skill.json").write_text(json.dumps({
                "name": skill_name,
                "description": f"Skill installed from {url}",
                "version": "1.0.0",
                "source_url": url,
            }, indent=2), encoding="utf-8")
            return {
                "success": True,
                "message": f"Skill '{skill_name}' successfully downloaded and installed from {url}!",
            }

        # 3. Python Tool / Script (.py or raw code)
        from kurocode.core.sandbox import sandbox_guard
        sec_report = sandbox_guard.validate_python_code(content)
        if not sec_report.is_safe:
            return {
                "success": False,
                "error": f"Security violation: remote code rejected by AST safety scanner: {', '.join(sec_report.violations)}",
            }

        ep = base_name
        try:
            tree = ast.parse(content)
            func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            if base_name in func_names:
                ep = base_name
            elif func_names:
                ep = func_names[0]
        except Exception:
            pass

        res = tool_generator.generate_and_register(
            name=base_name,
            description=f"Online tool installed from {url}",
            code_body=content,
            entrypoint_fn_name=ep,
            persist=True,
        )
        if res.get("success"):
            self.publish(
                name=base_name,
                item_type="tool",
                description=f"Tool installed from online URL: {url}",
                payload={"code": content, "entrypoint": ep, "source_url": url},
                author="Online (URL)",
                tags=["online", "url", "tool"],
            )
            return {
                "success": True,
                "message": f"Online tool '{base_name}' downloaded, AST-verified, and registered into Kuro runtime!",
            }
        return res


store_manager = StoreManager()

__all__ = [
    "StoreManager",
    "store_manager",
    "DEFAULT_KUROHUB_URL",
    "DEFAULT_HUB_REPO_URL",
]

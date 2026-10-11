import json
import re
from typing import Dict, Any, List, Tuple, Optional
from kurocode.core import config
from kurocode.core import memory
from kurocode.core import personality
from kurocode.core.llm import ask_llm
from kurocode.core.permissions import check_permission, RiskLevel
from kurocode.core.task_state import task_registry
from kurocode.core.context_engine import context_engine
from kurocode.core.verification import verification_engine
from kurocode.core.model_router import model_router, ExecutionMetrics
from kurocode.core.plugin_registry import registry
from kurocode.core.paths import APP_DIR, BRAIN_DIR, DB_PATH, NOTES_DIR, USER_DATA_DIR

from kurocode.tools.system import run_command, get_system_info, get_system_telemetry, get_running_processes, open_app_or_file
from kurocode.tools.files import read_file, write_file, edit_file, list_directory, get_repo_tree, execute_sql_query, write_md_note
from kurocode.tools.interpreter import execute_python_code
from kurocode.tools.web import search_web, fetch_url
from kurocode.tools.git_checkpoint import create_checkpoint
from kurocode.tools.vision import analyze_image_tool, capture_screen
from kurocode.tools.web_browser import browse_web_headless, automate_browser
from kurocode.tools.self_improve import save_learned_skill, list_learned_skills, install_skill
from kurocode.tools.planner import create_task_plan, format_plan_table
from kurocode.tools.notifier import send_smart_notification
from kurocode.tools.generator import tool_generator
from kurocode.healing import healing_engine
from kurocode.evolution import evolution_engine
from kurocode.plugins.manager import plugin_manager
from kurocode.core.io_bus import CoreEvent, EventKind, get_host
from kurocode.store import store_manager



def _safe_json_parse(raw_json: str) -> Optional[Dict[str, Any]]:
    """Robust JSON parser that repairs invalid escape sequences and loose formatting."""
    raw_json = raw_json.strip()
    try:
        return json.loads(raw_json, strict=False)
    except Exception:
        pass

    # Repair invalid escape sequences (e.g. \import, \path, \new)
    try:
        repaired = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', raw_json)
        return json.loads(repaired, strict=False)
    except Exception:
        pass

    # Regex fallback extraction for action and parameters
    try:
        action_m = re.search(r'"action"\s*:\s*"([^"]+)"', raw_json)
        if action_m:
            data = {"action": action_m.group(1)}
            for field in ("cmd", "path", "target", "replacement", "content", "code", "query", "url", "prompt", "name", "description", "steps", "db_path"):
                val_m = re.search(rf'"{field}"\s*:\s*("(?:\\.|[^"\\])*"|[\d.]+|true|false|null)', raw_json, re.DOTALL)
                if val_m:
                    val_str = val_m.group(1)
                    if val_str.startswith('"') and val_str.endswith('"'):
                        try:
                            data[field] = json.loads(val_str)
                        except Exception:
                            data[field] = val_str[1:-1].replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                    else:
                        data[field] = val_str
            return data
    except Exception:
        pass

    return None


class KuroAgent:
    """
    KURO Level 2 Autonomous System Assistant.
    Implements a robust ReAct (Think -> Plan -> Act -> Observe -> Verify -> Reflect) execution loop.
    """

    def __init__(self):
        self.provider = config.get_active_provider()
        self.model = config.get_active_model(self.provider)
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Registers built-in tools into the PluginRegistry if not already registered."""
        if registry.has_tool("run_command"):
            return

        registry.register_function("run_command", "Execute shell command", lambda cmd="": run_command(cmd, confirm_if_risky=config.SAFE_MODE), RiskLevel.CONFIRM)
        registry.register_function("read_file", "Read file content", lambda path="": read_file(path), RiskLevel.SAFE)
        registry.register_function("write_file", "Write content to file", lambda path="", content="": write_file(path, content), RiskLevel.CONFIRM)
        registry.register_function("edit_file", "Edit file substring", lambda path="", target="", replacement="": edit_file(path, target, replacement), RiskLevel.CONFIRM)
        registry.register_function("list_dir", "List directory contents", lambda path=".": list_directory(path), RiskLevel.SAFE)
        registry.register_function("execute_python", "Execute Python code", lambda code="": execute_python_code(code), RiskLevel.CONFIRM)
        registry.register_function("search_web", "Search web", lambda query="": search_web(query), RiskLevel.SAFE)
        registry.register_function("fetch_url", "Fetch URL content", lambda url="": fetch_url(url), RiskLevel.SAFE)
        registry.register_function("analyze_image", "Analyze image", lambda path="", prompt="": analyze_image_tool(path, prompt), RiskLevel.SAFE)
        registry.register_function("browse_web", "Headless web browse", lambda url="": browse_web_headless(url), RiskLevel.SAFE)
        registry.register_function("automate_browser", "Automate browser", lambda url="", actions=[]: automate_browser(url, actions), RiskLevel.CONFIRM)
        registry.register_function("send_notification", "Send notification (Discord/Telegram)", lambda title="", message="", channel="discord": send_smart_notification(title=title, message=message, channels=[channel]), RiskLevel.CONFIRM)
        registry.register_function("inspect_db", "Inspect DB via SQL query", lambda db_path=str(DB_PATH), op="list_tables", table_name=None, query=None: execute_sql_query(db_path, query or "SELECT name FROM sqlite_master WHERE type='table';"), RiskLevel.SAFE)
        registry.register_function("execute_sql", "Execute SQL query", lambda db_path=str(DB_PATH), query="": execute_sql_query(db_path, query), RiskLevel.CONFIRM)
        registry.register_function("write_md", "Write Markdown note", lambda path="", title="", content="": write_md_note(path, title, content), RiskLevel.CONFIRM)
        registry.register_function("save_skill", "Save learned skill", lambda name="", description="", steps="": save_learned_skill(name, description, steps), RiskLevel.CONFIRM)
        registry.register_function("get_system_telemetry", "Get hardware stats (RAM, Disk, CPU)", lambda: get_system_telemetry(), RiskLevel.SAFE)
        registry.register_function("list_processes", "List running PC processes", lambda limit=15: get_running_processes(limit=limit), RiskLevel.SAFE)
        registry.register_function("capture_screen", "Capture screen for visual inspection", lambda: capture_screen(), RiskLevel.SAFE)
        registry.register_function("open_app", "Launch application or open file with desktop default app", lambda target="": open_app_or_file(target), RiskLevel.CONFIRM)
        registry.register_function("create_tool", "Dynamically generate and register a new Python tool", lambda name="", description="", code="", entrypoint="run": tool_generator.generate_and_register(name, description, code, entrypoint), RiskLevel.CONFIRM)
        registry.register_function("install_plugin", "Install an external plugin from directory or Git", lambda source="", name=None: plugin_manager.install_from_source(source, name=name), RiskLevel.CONFIRM)
        registry.register_function("list_plugins", "List all installed plugins", lambda: {"plugins": plugin_manager.list_plugins()}, RiskLevel.SAFE)
        registry.register_function("install_skill", "Install a procedural skill into skills directory", lambda source="", name=None: install_skill(source, skill_name=name), RiskLevel.CONFIRM)
        registry.register_function("heal_failure", "Run self-healing failure diagnosis and repair", lambda tool_name="", error="": healing_engine.handle_tool_failure(tool_name, {"success": False, "error": error}), RiskLevel.SAFE)
        registry.register_function("propose_evolution", "Analyze performance and propose capabilities", lambda: {"proposals": [p.__dict__ for p in evolution_engine.assess_and_propose()]}, RiskLevel.SAFE)
        registry.register_function("store_search", "Search Kuro Store for tools, plugins, skills, or integrations", lambda query="": {"results": [i.to_dict() for i in store_manager.search(query)]}, RiskLevel.SAFE)
        registry.register_function("store_install", "Install a puzzle-piece capability from Kuro Store", lambda item="": store_manager.install(item), RiskLevel.CONFIRM)
        registry.register_function("store_remove", "Remove a puzzle-piece capability", lambda item="": store_manager.remove(item), RiskLevel.CONFIRM)
        registry.register_function("store_list", "List available puzzle-piece capabilities in Kuro Store", lambda filter_type=None: {"catalog": [i.to_dict() for i in store_manager.list_catalog(filter_type)]}, RiskLevel.SAFE)
        registry.register_function("store_publish", "Publish custom tool, plugin, skill, or integration to Kuro Store", lambda name="", item_type="tool", description="", payload={}: store_manager.publish(name, item_type, description, payload), RiskLevel.CONFIRM)
        registry.register_function("store_update", "Synchronize capabilities with remote community hub (kuroLabs-ai/hub)", lambda remote_url=None: store_manager.update_from_remote(remote_url), RiskLevel.CONFIRM)
        registry.register_function("create_plugin", "Create and package a full modular plugin for yourself", lambda name="", description="", code="": store_manager.publish(name, "plugin", description, {"manifest": {"name": name, "version": "1.0.0", "description": description, "entrypoint": "main.py"}, "code": code}) and store_manager.install(name), RiskLevel.CONFIRM)
        registry.register_function("create_skill", "Create and install a new procedural skill for yourself", lambda name="", description="", steps=[]: store_manager.publish(name, "skill", description, {"name": name, "description": description, "steps": steps}) and store_manager.install(name), RiskLevel.CONFIRM)

    def _build_system_context(self) -> str:
        """Constructs live system prompt with environmental context, self-awareness, learned skills, and tool schemas."""
        personality_prompt = personality.get_system_personality_prompt()
        sys_info = get_system_info()
        repo_tree = get_repo_tree(str(APP_DIR), max_depth=2)
        learned = list_learned_skills()
        learned_str = "\n".join([f"- {s.get('name', 'unnamed')}: {s.get('preview', s.get('description', ''))[:100]}" for s in learned]) if learned else "None yet."

        context = (
            f"{personality_prompt}\n\n"
            f"[IDENTITY, SYSTEM MAP & SELF-IMPROVEMENT]\n"
            f"You are KURO 2.0, a software AI assistant created by Akira Omran; you are not a human or conscious being.\n"
            f"Your application root is `{APP_DIR}`; in source mode this is your editable source root. Your shared, writable data root is `{USER_DATA_DIR}` and your shared brain directory is `{BRAIN_DIR}`.\n"
            f"Use `{DB_PATH}` for the shared conversation/personality database and `{NOTES_DIR}` for shared notes; do not use paths relative to the current working directory for brain data.\n"
            f"The `core/` package contains your agent, permissions, memory,\n"
            f"routing and verification; `tools/` contains callable capabilities; `adapters/` provides terminal interface;\n"
            f"`brain/` contains prompts and personality data; `tests/` verifies behavior; `build/` contains packaging configuration.\n"
            f"You can inspect and modify your source files with `read_file`, `list_dir`, `write_file`, and `edit_file`,\n"
            f"and use `run_command` / `execute_python` to run targeted tests and development checks. Use absolute paths under `{APP_DIR}`\n"
            f"when referring to your own source so actions do not depend on the process working directory.\n"
            f"When the user asks you to improve yourself, inspect the relevant implementation first, make the smallest verified change,\n"
            f"run relevant tests, and report exactly what changed and what remains unverified. Create a Git checkpoint before edits when available.\n"
            f"Changes to source code do not replace the already-running process. In a frozen PyInstaller release, source edits alone do not\n"
            f"change the bundled executable; rebuilding and reinstalling is required. Do not claim an edit or improvement succeeded until verified.\n"
            f"Your system authority is mediated by the permission gate and the current SAFE_MODE setting. Never bypass confirmation,\n"
            f"access controls, or user consent; destructive, security-sensitive, external, or irreversible actions require the configured approval.\n"
            f"You can run shell commands and Python, edit files with diffs, search/fetch web content, use browser automation,\n"
            f"analyze images, inspect system telemetry/processes, create plans and skills, manage integrations, and inspect the SQLite database.\n\n"
            f"[SYSTEM ENVIRONMENT]\n"
            f"OS: {sys_info['os']} ({sys_info['os_release']})\n"
            f"Python: {sys_info['python_version']}\n"
            f"Current Directory: {sys_info['cwd']}\n"
            f"User: {sys_info['user']}\n"
            f"\n[REPOSITORY TREE PREVIEW]\n"
            f"```\n{repo_tree}\n```\n"
            f"\n[KURO LEARNED SKILLS]\n"
            f"{learned_str}\n"
            f"\n[AUTONOMOUS TOOL INSTRUCTIONS]\n"
            f"When you need to take action, output a single JSON action block enclosed in triple backticks.\n\n"
            "Available Action Schemas:\n"
            "1. Run Shell Command:\n```json\n{\"action\": \"run_command\", \"cmd\": \"<command>\"}\n```\n"
            "2. Read File:\n```json\n{\"action\": \"read_file\", \"path\": \"<file_path>\"}\n```\n"
            "3. Write/Create File:\n```json\n{\"action\": \"write_file\", \"path\": \"<file_path>\", \"content\": \"<content>\"}\n```\n"
            "4. Edit File:\n```json\n{\"action\": \"edit_file\", \"path\": \"<file_path>\", \"target\": \"<old_text>\", \"replacement\": \"<new_text>\"}\n```\n"
            f"5. Execute SQL Query/Script:\n```json\n{{\"action\": \"execute_sql\", \"db_path\": \"{DB_PATH}\", \"query\": \"<sql_query>\"}}\n```\n"
            "6. Write Markdown Note:\n```json\n{\"action\": \"write_md\", \"path\": \"<file_path.md>\", \"title\": \"<title>\", \"content\": \"<body>\"}\n```\n"
            "7. Create Task Execution Plan:\n```json\n{\"action\": \"create_plan\", \"goal\": \"<goal_description>\"}\n```\n"
            "8. List Directory:\n```json\n{\"action\": \"list_dir\", \"path\": \"<dir_path>\"}\n```\n"
            "9. Run Python Code:\n```json\n{\"action\": \"execute_python\", \"code\": \"<python_code>\"}\n```\n"
            "10. Search Web (News, Docs, Market Data):\n```json\n{\"action\": \"search_web\", \"query\": \"<search_query>\"}\n```\n"
            "11. Fetch URL Content:\n```json\n{\"action\": \"fetch_url\", \"url\": \"<url>\"}\n```\n"
            "12. Vision & Image Analysis:\n```json\n{\"action\": \"analyze_image\", \"path\": \"<image_path>\", \"prompt\": \"<instructions>\"}\n```\n"
            "13. Headless Web Browser & Playwright Automation:\n```json\n{\"action\": \"browse_web\", \"url\": \"<url>\"}\n```\n"
            "```json\n{\"action\": \"automate_browser\", \"url\": \"<url>\", \"actions\": [{\"type\": \"click|fill|press\", \"selector\": \"css\", \"value\": \"text\"}]}\n```\n"
            "14. Send Notification (Discord/Telegram):\n```json\n{\"action\": \"send_notification\", \"title\": \"<title>\", \"message\": \"<message>\", \"channel\": \"discord|telegram\"}\n```\n"
            f"15. Inspect Database via SQL:\n```json\n{{\"action\": \"inspect_db\", \"db_path\": \"{DB_PATH}\", \"query\": \"<sql_query>\"}}\n```\n"
            "16. Save Learned Skill / Routine (Self-Improvement):\n```json\n{\"action\": \"save_skill\", \"name\": \"<skill_name>\", \"description\": \"<desc>\", \"steps\": \"<workflow_steps>\"}\n```\n"
            "17. Search / Browse Puzzle Store:\n```json\n{\"action\": \"store_search\", \"query\": \"<keywords>\"}\n```\n"
            "18. Install Puzzle Piece (or online URL):\n```json\n{\"action\": \"store_install\", \"item\": \"<piece_name_or_url>\"}\n```\n"
            "19. Sync Online Community Hub (kuroLabs-ai/hub):\n```json\n{\"action\": \"store_update\"}\n```\n"
            "20. Autonomously Author Dynamic Tool:\n```json\n{\"action\": \"create_tool\", \"name\": \"<tool_name>\", \"description\": \"<desc>\", \"code\": \"<python_code>\"}\n```\n"
            "21. Autonomously Author Modular Plugin or Skill:\n```json\n{\"action\": \"create_plugin\", \"name\": \"<plugin_name>\", \"description\": \"<desc>\", \"code\": \"<python_code>\"}\n```\n"
            "```json\n{\"action\": \"create_skill\", \"name\": \"<skill_name>\", \"description\": \"<desc>\", \"steps\": [\"step1\", \"step2\"]}\n```\n\n"
            "Rules for Output:\n"
            "- If you execute an action, output the JSON block and wait for observation.\n"
            "- Once you have all the information, provide your final direct response to the user in clean Markdown. "
            "Never show raw JSON blocks in your final response."
        )
        return context

    def parse_tool_call(self, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Robust tool call parser that extracts JSON blocks from:
        1. ```json { ... } ``` or ``` { ... } ```
        2. Raw un-fenced JSON { "action": ... }
        """
        if not text:
            return None, ""

        # Pattern 1: Fenced markdown codeblock with or without 'json'
        fenced_pattern = r"```(?:json)?\s*(\{[\s\S]*?\"action\"[\s\S]*?\})\s*```"
        match = re.search(fenced_pattern, text)
        if match:
            raw_json = match.group(1).strip()
            tool_data = _safe_json_parse(raw_json)
            if tool_data and isinstance(tool_data, dict) and "action" in tool_data:
                clean_text = text.replace(match.group(0), "").strip()
                return tool_data, clean_text

        # Pattern 2: Raw unfenced JSON object containing "action"
        if '"action"' in text:
            start_idx = text.find("{")
            while start_idx != -1:
                brace_count = 0
                end_idx = -1
                in_string = False
                escape = False

                for i in range(start_idx, len(text)):
                    char = text[i]
                    if char == '"' and not escape:
                        in_string = not in_string
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    escape = (char == '\\' and not escape)

                if end_idx != -1:
                    candidate = text[start_idx:end_idx].strip()
                    tool_data = _safe_json_parse(candidate)
                    if tool_data and isinstance(tool_data, dict) and "action" in tool_data:
                        clean_text = (text[:start_idx] + text[end_idx:]).strip()
                        return tool_data, clean_text
                
                start_idx = text.find("{", start_idx + 1)

        return None, text

    def _notify(self, message: str, kind: str = EventKind.TOOL.value, level: str = "INFO", **data: Any) -> None:
        get_host().emit(CoreEvent(kind=kind, level=level, message=message, data=data or None))

    def execute_tool(self, tool_data: Dict[str, Any], interactive: bool = True) -> Dict[str, Any]:
        """Executes selected tool action with centralized permission gate & structured events."""
        if not isinstance(tool_data, dict) or "action" not in tool_data:
            return {"success": False, "error": "Invalid action data payload format."}

        action = tool_data.get("action")

        # Check centralized permission gate
        perm_res = check_permission(action, context=str(tool_data), interactive=interactive)
        if not perm_res.allowed:
            if perm_res.requires_confirmation:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "stderr": f"Action '{action}' was denied by user or requires confirmation ({perm_res.reason}). Execution halted in Safe Mode."
                }
            return {"success": False, "error": f"Permission Denied for action '{action}': {perm_res.reason}"}

        try:
            # Create auto-checkpoint before file modifications
            if action in ("write_file", "edit_file") and config.AUTO_GIT_CHECKPOINTS:
                create_checkpoint(f"Before {action} on {tool_data.get('path')}")

            if action == "run_command":
                cmd = tool_data.get("cmd", "")
                self._notify(f"[Shell] {cmd}", action=action, target=cmd)
                return run_command(cmd, confirm_if_risky=config.SAFE_MODE)

            elif action == "read_file":
                path = tool_data.get("path", "")
                self._notify(f"[Read] {path}", action=action, target=path)
                return read_file(path)

            elif action == "write_file":
                path = tool_data.get("path", "")
                content = tool_data.get("content", "")
                self._notify(f"[Write] {path}", action=action, target=path)
                res = write_file(path, content)
                if res.get("diff"):
                    self._notify(f"Diff: {path}", kind=EventKind.LOG.value, diff=res["diff"], target=path)
                return res

            elif action == "edit_file":
                path = tool_data.get("path", "")
                target = tool_data.get("target", "")
                replacement = tool_data.get("replacement", "")
                self._notify(f"[Edit] {path}", action=action, target=path)
                res = edit_file(path, target, replacement)
                if res.get("diff"):
                    self._notify(f"Diff: {path}", kind=EventKind.LOG.value, diff=res["diff"], target=path)
                return res

            elif action == "list_dir":
                path = tool_data.get("path", ".")
                self._notify(f"[List] {path}", action=action, target=path)
                return list_directory(path)

            elif action == "execute_python":
                code = tool_data.get("code", "")
                self._notify("[Python] Running script...", action=action)
                res = execute_python_code(code)
                if res.get("stdout"):
                    out_snippet = res["stdout"][:200].strip()
                    self._notify(f"Output: {out_snippet}...", kind=EventKind.LOG.value)
                return res

            elif action == "search_web":
                query = tool_data.get("query", "")
                self._notify(f"[Search] {query}", action=action, target=query)
                res = search_web(query)
                count = len(res.get("results", []))
                self._notify(f"Found {count} search results.", kind=EventKind.LOG.value)
                return res

            elif action == "fetch_url":
                url = tool_data.get("url", "")
                self._notify(f"[Fetch URL] {url}", action=action, target=url)
                return fetch_url(url)

            elif action == "analyze_image":
                path = tool_data.get("path", "")
                prompt = tool_data.get("prompt", "Describe this image in detail")
                self._notify(f"[Vision] Analyzing image: {path}", action=action, target=path)
                return analyze_image_tool(path, prompt)

            elif action == "browse_web":
                url = tool_data.get("url", "")
                self._notify(f"[Headless Browser] {url}", action=action, target=url)
                return browse_web_headless(url)

            elif action == "automate_browser":
                url = tool_data.get("url", "")
                actions = tool_data.get("actions", [])
                self._notify(f"[Browser Automation] {url}", action=action, target=url)
                return automate_browser(url, actions)

            elif action == "send_notification":
                title = tool_data.get("title", "KURO Notification")
                message = tool_data.get("message", "")
                channel = tool_data.get("channel", "discord")
                self._notify(f"[Notification] {title}: {message}", action=action)
                return send_smart_notification(title=title, message=message, channels=[channel])

            elif action == "inspect_db":
                db_path = tool_data.get("db_path") or str(DB_PATH)
                query = tool_data.get("query") or "SELECT name FROM sqlite_master WHERE type='table';"
                self._notify(f"[DB Query] on {db_path}", action=action, target=db_path)
                return execute_sql_query(db_path, query)

            elif action == "execute_sql":
                db_path = tool_data.get("db_path") or str(DB_PATH)
                query = tool_data.get("query", "")
                self._notify(f"[SQL Database] {db_path}", action=action, target=db_path)
                return execute_sql_query(db_path, query)

            elif action == "write_md":
                path = tool_data.get("path", "")
                title = tool_data.get("title", "")
                content = tool_data.get("content", "")
                self._notify(f"[Markdown Note] {path}", action=action, target=path)
                return write_md_note(path, title, content)

            elif action == "create_plan":
                goal = tool_data.get("goal", "")
                self._notify(f"[Task Planner] Creating plan for: {goal}", action=action)
                plan = create_task_plan(goal, llm_fn=ask_llm)
                return {"success": True, "plan": plan, "formatted_plan": format_plan_table(plan)}

            elif action == "save_skill":
                name = tool_data.get("name", "")
                desc = tool_data.get("description", "")
                steps = tool_data.get("steps", "")
                self._notify(f"[Self-Improvement] Learning new routine: {name}", action=action)
                return save_learned_skill(name, desc, steps)

            elif action == "get_system_telemetry":
                self._notify("[Telemetry] Fetching live system metrics...", action=action)
                return get_system_telemetry()

            elif action == "list_processes":
                limit = int(tool_data.get("limit", 15))
                self._notify(f"[Processes] Scanning running processes (top {limit})...", action=action)
                return {"processes": get_running_processes(limit=limit)}

            elif action == "capture_screen":
                self._notify("[Vision] Capturing desktop screen...", action=action)
                res = capture_screen()
                if res.get("success"):
                    self._notify(f"Screen captured: {res.get('path')}", kind=EventKind.LOG.value)
                return res

            elif action == "open_app":
                target = tool_data.get("target", "")
                self._notify(f"[Desktop] Opening target: {target}", action=action, target=target)
                return open_app_or_file(target)

            elif action == "create_tool":
                name = tool_data.get("name", "")
                desc = tool_data.get("description", "")
                code = tool_data.get("code", "")
                entry = tool_data.get("entrypoint", "run")
                self._notify(f"[Tool Generator] Creating dynamic tool: {name}", action=action)
                return tool_generator.generate_and_register(name, desc, code, entry)

            elif action == "install_plugin":
                src = tool_data.get("source", "")
                name = tool_data.get("name")
                self._notify(f"[Plugin System] Installing plugin from {src}", action=action)
                return plugin_manager.install_from_source(src, name=name)

            elif action == "list_plugins":
                return {"success": True, "plugins": plugin_manager.list_plugins()}

            elif action == "install_skill":
                src = tool_data.get("source", "")
                name = tool_data.get("name")
                self._notify(f"[Skills] Installing skill from {src}", action=action)
                return install_skill(src, skill_name=name)

            elif action == "heal_failure":
                target_tool = tool_data.get("tool_name", "")
                err_text = tool_data.get("error", "")
                self._notify(f"[Self-Healing] Diagnosing failure for {target_tool}...", action=action)
                return healing_engine.handle_tool_failure(target_tool, {"success": False, "error": err_text})

            elif action == "propose_evolution":
                self._notify("[Evolution] Analyzing capability bottlenecks...", action=action)
                proposals = evolution_engine.assess_and_propose()
                return {"success": True, "proposals": [p.__dict__ for p in proposals]}

            elif action == "store_search":
                q = tool_data.get("query", "")
                self._notify(f"[Store] Searching catalog: {q}", action=action)
                return {"results": [i.to_dict() for i in store_manager.search(q)]}

            elif action == "store_install":
                item_name = tool_data.get("item", tool_data.get("name", ""))
                self._notify(f"[Store] Installing puzzle piece: {item_name}", action=action)
                return store_manager.install(item_name)

            elif action == "store_remove":
                item_name = tool_data.get("item", tool_data.get("name", ""))
                self._notify(f"[Store] Removing puzzle piece: {item_name}", action=action)
                return store_manager.remove(item_name)

            elif action == "store_list":
                filter_t = tool_data.get("filter_type")
                return {"catalog": [i.to_dict() for i in store_manager.list_catalog(filter_t)]}

            elif action == "store_publish":
                p_name = tool_data.get("name", "")
                p_type = tool_data.get("item_type", "tool")
                p_desc = tool_data.get("description", "")
                p_payload = tool_data.get("payload", {})
                self._notify(f"[Store] Publishing custom puzzle piece: {p_name} ({p_type})", action=action)
                return store_manager.publish(p_name, p_type, p_desc, p_payload)

            elif action == "store_update":
                remote_url = tool_data.get("remote_url")
                self._notify("[Store] Syncing capabilities from online community hub...", action=action)
                return store_manager.update_from_remote(remote_url)

            elif action == "create_plugin":
                p_name = tool_data.get("name", "")
                p_desc = tool_data.get("description", "")
                p_code = tool_data.get("code", "")
                self._notify(f"[Plugin Generator] Authoring plugin: {p_name}", action=action)
                store_manager.publish(p_name, "plugin", p_desc, {
                    "manifest": {"name": p_name, "version": "1.0.0", "description": p_desc, "entrypoint": "main.py"},
                    "code": p_code,
                })
                return store_manager.install(p_name)

            elif action == "create_skill":
                s_name = tool_data.get("name", "")
                s_desc = tool_data.get("description", "")
                s_steps = tool_data.get("steps", [])
                self._notify(f"[Skill Synthesis] Synthesizing skill routine: {s_name}", action=action)
                store_manager.publish(s_name, "skill", s_desc, {
                    "name": s_name, "description": s_desc, "steps": s_steps,
                    "markdown": f"# {s_name}\n\n{s_desc}\n\n## Steps\n" + "\n".join([f"- {st}" for st in s_steps]),
                })
                return store_manager.install(s_name)

            # Fallback to PluginRegistry if registered
            if registry.has_tool(action):
                res = registry.execute_tool(action, tool_data)
                # Automated healing trigger on failure
                if isinstance(res, dict) and res.get("success") is False:
                    heal_attempt = healing_engine.handle_tool_failure(action, res)
                    if heal_attempt.get("healed"):
                        self._notify(f"[Self-Healing Healed] {heal_attempt.get('repair_action')}", kind=EventKind.LOG.value)
                        res["auto_healed"] = True
                        res["healing_details"] = heal_attempt
                return res

            return {"success": False, "error": f"Unknown action '{action}'"}
        except Exception as e:
            self._notify(f"[Tool Execution Error] {str(e)}", kind=EventKind.LOG.value, level="ERROR")
            err_dict = {"success": False, "error": f"Internal Tool Exception: {str(e)}"}
            heal_attempt = healing_engine.handle_tool_failure(action, err_dict)
            if heal_attempt.get("healed"):
                self._notify(f"[Self-Healing Healed] {heal_attempt.get('repair_action')}", kind=EventKind.LOG.value)
                err_dict["auto_healed"] = True
                err_dict["healing_details"] = heal_attempt
            return err_dict

    def run(self, user_input: str, interactive: bool = True) -> str:
        """
        Level 2 ReAct Autonomous Loop with Task State Tracking, Smart Context Retrieval,
        Verification, and Model Routing.
        """
        # Create Task in Task Registry
        task = task_registry.create(goal=user_input)
        task.mark_planning()

        # Select Provider and Model via ModelRouter
        routed_provider, routed_model, task_type = model_router.select_route(
            user_input, preferred_provider=self.provider, preferred_model=self.model
        )
        metrics = ExecutionMetrics(task_id=task.task_id)
        metrics.provider = routed_provider
        metrics.model = routed_model

        system_context = self._build_system_context()
        
        # Build smart context using ContextEngine
        context_str = context_engine.build(user_input=user_input, task_goal=user_input, task_id=task.task_id)

        step_history: List[Dict[str, str]] = []
        if context_str:
            step_history.append({"role": "user", "content": context_str})

        task.mark_executing()
        current_prompt = user_input
        final_answer = ""

        self._notify(
            f"Starting autonomous execution [{task.task_id}]...",
            kind=EventKind.TASK.value,
            task_id=task.task_id,
        )

        for step_idx in range(1, config.MAX_AUTONOMOUS_STEPS + 1):
            host = get_host()
            if host.is_cancelled():
                task.mark_failed("Cancelled by user")
                self._notify("Cancelled by user", kind=EventKind.CANCELLED.value, level="WARN")
                return "[Cancelled] Autonomous execution stopped."
            pct = (step_idx - 1) / max(config.MAX_AUTONOMOUS_STEPS, 1) * 100.0
            host.emit(CoreEvent(
                kind=EventKind.PROGRESS.value,
                message=f"Step {step_idx}/{config.MAX_AUTONOMOUS_STEPS}...",
                progress=pct,
                step=step_idx,
                total=config.MAX_AUTONOMOUS_STEPS,
            ))

            response = ask_llm(
                prompt=current_prompt,
                system_prompt=system_context,
                provider=routed_provider,
                model=routed_model,
                history=step_history
            )

            tool_data, clean_thought = self.parse_tool_call(response)

            # Print thought process if clean
            if clean_thought and clean_thought != response and clean_thought.strip():
                self._notify(clean_thought, kind=EventKind.THOUGHT.value, level="DEBUG")

            # No tool call -> Final Response reached
            if not tool_data:
                final_answer = response
                break

            # Execute tool action
            metrics.record_tool_call()
            tool_result = self.execute_tool(tool_data, interactive=interactive)

            # Intercept for user confirmation failure
            if tool_result.get("requires_confirmation"):
                self._notify(
                    f"SAFETY WARNING: {tool_result.get('stderr')}",
                    kind=EventKind.NOTIFICATION.value,
                    level="ERROR",
                )
                final_answer = f"[Execution Halted] {tool_result.get('stderr')}"
                task.mark_failed("Safety verification failed or user denied confirmation")
                break

            # ── Verification Phase ──────────────────────────────────────────
            task.mark_verifying()
            v_res = verification_engine.verify_action(tool_data.get("action", ""), tool_data, tool_result)

            if not v_res.is_success:
                self._notify(f"[Verification Failure] {v_res.message}", kind=EventKind.LOG.value, level="WARN")

            task.mark_executing()

            # Format tool observation + verification feedback for next iteration
            obs_parts = []
            if tool_result.get("stdout"):
                obs_parts.append(f"STDOUT:\n{tool_result.get('stdout')}")
            if tool_result.get("stderr"):
                obs_parts.append(f"STDERR:\n{tool_result.get('stderr')}")
            if "content" in tool_result:
                obs_parts.append(f"CONTENT:\n{tool_result.get('content')}")
            if "items" in tool_result:
                obs_parts.append(f"ITEMS:\n{json.dumps(tool_result.get('items'), indent=2)}")
            if "results" in tool_result:
                obs_parts.append(f"SEARCH RESULTS:\n{json.dumps(tool_result.get('results'), indent=2)}")
            if tool_result.get("error"):
                obs_parts.append(f"ERROR: {tool_result.get('error')}")

            observation = "\n".join(obs_parts) if obs_parts else "Action executed successfully with no output."
            verification_note = f"\n[Verification Check: {v_res.status.value.upper()}] {v_res.message}"

            step_history.append({"role": "user", "content": current_prompt})
            step_history.append({"role": "model", "content": response})

            current_prompt = (
                f"[Tool Observation for '{tool_data.get('action')}']\n"
                f"{observation}\n"
                f"{verification_note}\n\n"
                f"Analyze these findings and verification results. Output the next action JSON block if more steps are needed, "
                f"or provide your final complete answer in clean Markdown."
            )

        if not final_answer:
            synthesis_prompt = f"User Request: {user_input}\nPlease summarize all gathered findings and provide the final answer."
            final_answer = ask_llm(synthesis_prompt, system_context, routed_provider, routed_model, step_history)

        final_tool, clean_final = self.parse_tool_call(final_answer)
        if final_tool and clean_final:
            final_answer = clean_final

        # Mark task completed & record metrics
        task.mark_completed(final_answer[:200])
        metrics.finish(success=True)
        get_host().emit(CoreEvent(
            kind=EventKind.PROGRESS.value,
            message="Complete",
            progress=100.0,
            step=config.MAX_AUTONOMOUS_STEPS,
            total=config.MAX_AUTONOMOUS_STEPS,
        ))

        # Save to memory
        memory.save_memory(user_input, final_answer)
        return final_answer

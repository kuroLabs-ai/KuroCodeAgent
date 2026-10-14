"""
adapters/cli.py — KURO CLI Presentation Adapter

Extracts the full interactive REPL and slash-command handling from main.py
into a clean CLIAdapter class that integrates with the core/io_bus.py
CallbackHost / IOHost system.

Responsibilities:
  - Interactive REPL (slash commands, shell passthrough, agent chat)
  - Headless single-shot mode (--query / JSON output)
  - Event rendering (_on_event) and interactive prompts (_on_request)
  - Typewriter response display with optional background TTS
  - All UI helpers: spinner, panels, tables, status banner, help

Imports and Unicode/encoding fixups are replicated exactly from main.py
to ensure the adapter works identically whether launched from main.py or
imported directly.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Standard-library bootstrap — must come before any rich/prompt_toolkit import
# ─────────────────────────────────────────────────────────────────────────────
import sys
import os
import json
import time
import threading

# Suppress pygame startup banner before any import triggers it
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Fix for rich._unicode_data version resolution
# (prevents "No module named 'rich._unicode_data.unicode17-0-0'")
os.environ.setdefault("UNICODE_VERSION", "15.1.0")

# Force UTF-8 output on Windows so Rich spinners and Unicode chars work
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# Bulletproof compatibility patch for Rich unicode data tables
try:
    import importlib
    import rich._unicode_data
    import rich.cells
    from rich.cells import CellTable

    _cached_cell_table = None
    for _ver in ("15-1-0", "15-0-0", "14-0-0", "13-0-0", "12-1-0", "17-0-0", "16-0-0", "10-0-0"):
        try:
            _m = importlib.import_module(f"rich._unicode_data.unicode{_ver}")
            if hasattr(_m, "cell_table") and isinstance(_m.cell_table, CellTable):
                _cached_cell_table = _m.cell_table
                break
        except Exception:
            continue

    if _cached_cell_table is None:
        _cached_cell_table = CellTable(
            unicode_version="15.1.0",
            widths=((0, 0x10FFFF, 1),),
            narrow_to_wide=frozenset(),
        )

    def _bulletproof_unicode_load(unicode_version="auto"):
        return _cached_cell_table

    rich._unicode_data.load = _bulletproof_unicode_load
    rich.cells.load_cell_table = _bulletproof_unicode_load
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Rich imports
# ─────────────────────────────────────────────────────────────────────────────
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich import box

# ─────────────────────────────────────────────────────────────────────────────
# Prompt-toolkit imports
# ─────────────────────────────────────────────────────────────────────────────
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import PathCompleter, Completer, Completion
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.lexers import SimpleLexer
import html  # stdlib — must come after prompt_toolkit so no naming conflict

# ─────────────────────────────────────────────────────────────────────────────
# Core / tool imports
# ─────────────────────────────────────────────────────────────────────────────
from kurocode.core import config
from kurocode.core.paths import NOTES_DIR
from kurocode.core import memory
from kurocode.core.llm import ask_llm
from kurocode.core.agent import KuroAgent
from kurocode.core.paths import DB_PATH, HISTORY_FILE
from kurocode.core import io_bus
from kurocode.core.io_bus import (
    CallbackHost,
    NullHost,
    CoreEvent,
    InputRequest,
    EventKind,
    PromptKind,
)
from kurocode.tools.system import run_command, get_system_telemetry, get_running_processes, open_app_or_file
from kurocode.tools.git_checkpoint import rollback_checkpoint
from kurocode.tools.web import search_web
from kurocode.tools.vision import capture_screen
from kurocode.tools.files import execute_sql_query, write_md_note
from kurocode.tools.planner import create_task_plan, get_active_plan, execute_plan_step, format_plan_table
from kurocode.tools.self_improve import save_learned_skill, list_learned_skills
from kurocode.tools.notifier import send_smart_notification


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
CAT_LOGO = r"""[bold cyan]
       _                        
       \`*-.                    
        )  _`-.                 
       .  : `. .                
       : _   '  \               
       ; *` _.   `*-._          
       `-.-'          `-.       
         ;       `       `.     
         :.       .        \    
         . \  .   :   .-'   .   
         '  `+.;  ;  '      :   
         :  '  |    ;       ;-. 
         ; '   : :`-:     _.`* ;
       .*' /  .*' ; .*`- +'  `*' 
      `*-*   `*-*  `*-*'[/bold cyan]"""

KURO_TITLE = "[bold cyan]K[/][bold white]U[/][bold cyan]R[/][bold white]O[/]"

BANNER_LINES = [
    "",
    f"   {KURO_TITLE}  [dim]v2.0[/dim]  [bold cyan]Autonomous Terminal Intelligence[/]",
    "   [dim]ReAct 2.0  |  Context Engine  |  Encrypted Vault  |  Sandbox Guard  |  Integrations[/]",
    "",
]

# Essential system commands kept in slash menu
COMMAND_LIST = [
    "/help", "/store", "/hub", "/vault", "/key", "/models", "/status",
    "/safe", "/pool", "/undo", "/clear", "/memory", "/system",
    "/top", "/skills", "/plugin", "/integrations",
    "exit", "quit",
]

SLASH_DESCRIPTIONS = {
    "/help":         "Show command reference & capabilities",
    "/store":        "KuroHub Store: /store <list|search <q>|install <name>|remove <name>|update>",
    "/hub":          "KuroHub Store: /hub <list|search <q>|install <name>|remove <name>|update>",
    "/vault":        "Encrypted credential vault: /vault <set|get|list|delete|lock|unlock>",
    "/key":          "Add API key: /key <KEY> or /key <provider> <KEY>",
    "/models":       "Model fallback priority chain & provider inspection",
    "/status":       "Active provider, model, & safe mode status",
    "/safe":         "Toggle Safe Mode & permission prompts: /safe <on|off|toggle|status>",
    "/pool":         "API key pool & cooldown status",
    "/undo":         "Rollback last automated file changes",
    "/clear":        "Reset active conversation memory",
    "/memory":       "View stored conversation history & brain summary",
    "/system":       "Live PC hardware telemetry (CPU, RAM, Disk, OS)",
    "/top":          "List active running processes & memory footprint",
    "/skills":       "List all KURO self-learned skills",
    "/plugin":       "Manage plugins: /plugin <list|install <source>|remove <name>>",
    "/integrations": "Manage connected services (GitHub, Google Drive, GitLab)",
}


def _get_installed_skills_map() -> dict[str, str]:
    """Returns a mapping of /skill-name to its description for autocomplete and dispatch."""
    skills_map: dict[str, str] = {}
    try:
        from kurocode.brain.kuro_hub import get_skills_kurohub
        for slug, item in get_skills_kurohub().items():
            cmd_name = f"/{slug.replace('_', '-')}"
            skills_map[cmd_name] = item.get("description", "Installed procedural skill")
    except Exception:
        pass

    try:
        from kurocode.tools.self_improve import list_learned_skills
        for s in list_learned_skills():
            slug = s.get("slug", s.get("name", ""))
            cmd_name = f"/{slug.replace('_', '-')}"
            if cmd_name not in skills_map:
                skills_map[cmd_name] = s.get("description", "Installed procedural skill")
    except Exception:
        pass
    return skills_map


# ─────────────────────────────────────────────────────────────────────────────
# Prompt-Toolkit Style — Modern Dark Terminal Theme
# ─────────────────────────────────────────────────────────────────────────────
PT_STYLE = Style.from_dict({
    # Prompt label
    "prompt.user":      "#00d7ff bold",
    "prompt.gt":        "#555555",
    # Input text
    "":                 "#e0e0e0",
    # Auto-suggest ghost text
    "auto-suggest":     "#444444 italic",
    # Completion menu
    "completion-menu.completion":              "bg:#1a1a2e #c0c0c0",
    "completion-menu.completion.current":      "bg:#00d7ff #000000 bold",
    "completion-menu.meta.completion":         "bg:#111111 #888888",
    "completion-menu.meta.completion.current": "bg:#007aa8 #ffffff",
    "scrollbar.background": "bg:#111111",
    "scrollbar.button":     "bg:#333333",
    # Validation error
    "validation-toolbar": "bg:#800000 #ffffff",
    # Bottom bar
    "bottom-toolbar": "bg:#111111 #555555",
})


# ─────────────────────────────────────────────────────────────────────────────
# KuroCompleter — Tab completion for slash commands, skills, and paths
# ─────────────────────────────────────────────────────────────────────────────
class KuroCompleter(Completer):
    """Combines essential slash commands and installed skills with autocomplete and path completion."""

    def __init__(self):
        self.path_completer = PathCompleter(only_directories=False, expanduser=True)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        # Dynamic skills map
        skills_map = _get_installed_skills_map()

        # Slash command and skill completion
        if text.startswith("/"):
            query_prefix = text.split()[0] if text.split() else "/"

            # 1. Essential system slash commands
            for cmd in COMMAND_LIST:
                if cmd.startswith(query_prefix):
                    raw_desc = SLASH_DESCRIPTIONS.get(cmd, "")
                    desc = html.escape(raw_desc)
                    cmd_escaped = html.escape(cmd)
                    yield Completion(
                        cmd,
                        start_position=-len(query_prefix),
                        display=HTML(f"<ansibrightcyan>{cmd_escaped}</ansibrightcyan>"),
                        display_meta=HTML(f"<ansidarkgray>{desc}</ansidarkgray>"),
                    )

            # 2. Installed skill commands (/skill-name)
            for skill_cmd, skill_desc in skills_map.items():
                if skill_cmd.startswith(query_prefix):
                    desc = html.escape(skill_desc[:60])
                    cmd_escaped = html.escape(skill_cmd)
                    yield Completion(
                        skill_cmd,
                        start_position=-len(query_prefix),
                        display=HTML(f"<ansigreen>{cmd_escaped}</ansigreen>"),
                        display_meta=HTML(f"<ansimagenta>[SKILL] {desc}</ansimagenta>"),
                    )
            return

        # Shell command path completion after '!'
        if text.startswith("!"):
            for c in self.path_completer.get_completions(document, complete_event):
                yield c
            return

        # Regular chat — suggest essential /commands and skills for quick access
        if not text:
            for cmd in COMMAND_LIST:
                raw_desc = SLASH_DESCRIPTIONS.get(cmd, "")
                desc = html.escape(raw_desc)
                cmd_escaped = html.escape(cmd)
                yield Completion(
                    cmd,
                    start_position=0,
                    display=HTML(f"<ansibrightcyan>{cmd_escaped}</ansibrightcyan>"),
                    display_meta=HTML(f"<ansidarkgray>{desc}</ansidarkgray>"),
                )
            for skill_cmd, skill_desc in skills_map.items():
                desc = html.escape(skill_desc[:60])
                cmd_escaped = html.escape(skill_cmd)
                yield Completion(
                    skill_cmd,
                    start_position=0,
                    display=HTML(f"<ansigreen>{cmd_escaped}</ansigreen>"),
                    display_meta=HTML(f"<ansimagenta>[SKILL] {desc}</ansimagenta>"),
                )


# ─────────────────────────────────────────────────────────────────────────────
# CLIAdapter
# ─────────────────────────────────────────────────────────────────────────────
class CLIAdapter:
    """
    Presentation adapter for KURO's terminal interface.

    Wraps the Rich console and prompt_toolkit PromptSession, implements
    IOHost callbacks for the io_bus, and drives the interactive REPL loop
    (run_interactive) as well as headless single-shot execution
    (run_headless).
    """

    def __init__(self):
        # Rich console — no automatic markup highlighting so we control all styles
        self.console = Console(highlight=False)

        # prompt_toolkit session (constructed lazily in run_interactive)
        self._session: PromptSession | None = None

        # Active CallbackHost for the current agent run (used for cancellation)
        self._host: CallbackHost | None = None

        # Key bindings wired to this adapter instance
        self._kb = self._build_key_bindings()

        # Completer for interactive prompts
        self.completer = KuroCompleter()


    # ─────────────────────────────────────────────────────────────────────────
    # Key bindings
    # ─────────────────────────────────────────────────────────────────────────
    def _build_key_bindings(self) -> KeyBindings:
        """Returns a KeyBindings object scoped to this adapter instance."""
        kb = KeyBindings()

        @kb.add("c-l")          # Ctrl+L → clear screen & redraw header
        def _clear(event):
            os.system("cls" if os.name == "nt" else "clear")
            self._print_header()

        @kb.add("c-c")          # Ctrl+C → cancel current run or exit prompt
        def _interrupt(event):
            if self._host is not None:
                # Mid-execution: cancel the agent run gracefully
                self._host.request_cancel()
            else:
                # Idle at prompt: exit the prompt app so EOFError propagates
                event.app.exit()

        return kb

    # ─────────────────────────────────────────────────────────────────────────
    # io_bus callbacks
    # ─────────────────────────────────────────────────────────────────────────
    def _on_event(self, event: CoreEvent) -> None:
        """Routes structured CoreEvents from the agent to rich console output."""
        kind = event.kind

        if kind == EventKind.LOG.value:
            level = event.level or "INFO"
            colour = {
                "DEBUG": "dim",
                "INFO":  "dim cyan",
                "WARN":  "yellow",
                "ERROR": "bold red",
            }.get(level, "dim")
            self.console.print(f"[{colour}]  {event.message}[/]")

        elif kind == EventKind.PROGRESS.value:
            step = event.step
            msg = event.message or ""
            # Derive a clean label: strip the raw "Step N/10..." pattern if present
            import re as _re
            label = _re.sub(r"^Step\s+\d+/\d+[.\s]*", "", msg).strip() or "Working"
            dot = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
            frame = dot[(step or 0) % len(dot)]
            self.console.print(
                f"\r  [cyan]{frame}[/]  [dim]{label}[/]" + " " * 10,
                end="",
            )

        elif kind == EventKind.TOOL.value:
            tool_name = event.data.get("tool", "?") if isinstance(event.data, dict) else "?"
            self.console.print(
                f"  [bold yellow]⚙ Tool:[/] [yellow]{tool_name}[/]  [dim]{event.message}[/]"
            )

        elif kind == EventKind.THOUGHT.value:
            self.console.print(f"  [dim italic]{event.message}[/]")

        elif kind == EventKind.NOTIFICATION.value:
            self.console.print(
                Panel(
                    event.message,
                    title="[bold cyan]KURO Notification[/]",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )

        elif kind == EventKind.STATUS.value:
            self.console.print(f"  [cyan]{event.message}[/]")

        elif kind == EventKind.CANCELLED.value:
            self.console.print("\n[bold yellow]  ⚠ Operation cancelled.[/]")

        # EventKind.RESPONSE and others are handled by the caller
        # (run_interactive receives the return value of agent.run())

    def _on_request(self, req: InputRequest):
        """
        Handles interactive input prompts from the agent (called synchronously
        by the CallbackHost when the domain layer needs user input).
        """
        from prompt_toolkit.shortcuts import confirm, prompt as pt_prompt

        kind = req.kind
        title = req.title or "KURO"
        message = req.message or title

        if kind == PromptKind.CONFIRM.value:
            self.console.print(
                Panel(
                    f"[bold yellow]{message}[/]",
                    title=f"[cyan]{title}[/]",
                    border_style="yellow",
                    padding=(0, 2),
                )
            )
            try:
                answer = pt_prompt("  Confirm? [y/N]: ").strip().lower()
                return answer in ("y", "yes", "1", "true")
            except (KeyboardInterrupt, EOFError):
                return False

        elif kind == PromptKind.TEXT.value:
            self.console.print(f"  [cyan]{message}[/]")
            try:
                return pt_prompt("  > ").strip()
            except (KeyboardInterrupt, EOFError):
                return req.default or ""

        elif kind == PromptKind.PASSWORD.value:
            self.console.print(f"  [cyan]{message}[/]")
            try:
                return pt_prompt("  > ", is_password=True).strip()
            except (KeyboardInterrupt, EOFError):
                return req.default or ""

        elif kind == PromptKind.SELECT.value:
            options = req.options or []
            self.console.print(f"\n  [bold cyan]{message}[/]")
            for i, opt in enumerate(options, 1):
                self.console.print(f"  [dim]{i}.[/] {opt}")
            try:
                raw = pt_prompt("  Choice (number or text): ").strip()
                if raw.isdigit():
                    idx = int(raw) - 1
                    if 0 <= idx < len(options):
                        return options[idx]
                if raw in options:
                    return raw
                return req.default if req.default is not None else (options[0] if options else None)
            except (KeyboardInterrupt, EOFError):
                return req.default if req.default is not None else (options[0] if options else None)

        elif kind == PromptKind.MULTISELECT.value:
            options = req.options or []
            self.console.print(f"\n  [bold cyan]{message}[/]")
            for i, opt in enumerate(options, 1):
                self.console.print(f"  [dim]{i}.[/] {opt}")
            try:
                raw = pt_prompt("  Selections (comma-separated numbers or 'all'): ").strip()
                if raw.lower() == "all":
                    return list(options)
                chosen = []
                for part in raw.split(","):
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(options):
                            chosen.append(options[idx])
                    elif part in options:
                        chosen.append(part)
                return chosen or (req.default or [])
            except (KeyboardInterrupt, EOFError):
                return req.default or []

        # FILE or unknown
        return req.default

    # ─────────────────────────────────────────────────────────────────────────
    # UI helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _get_bottom_toolbar(self):
        """Dynamic bottom toolbar for prompt_toolkit: provider | model | safe mode."""
        provider = html.escape(config.get_active_provider().upper())
        model = html.escape(config.get_active_model())
        safe = "SAFE" if config.SAFE_MODE else "UNSAFE"
        return HTML(
            f" <b><ansibrightcyan>KURO</ansibrightcyan></b>  "
            f"<ansidarkgray>|</ansidarkgray>  "
            f"<ansibrightgreen>{provider}</ansibrightgreen>  "
            f"<ansidarkgray>{model}</ansidarkgray>  "
            f"<ansidarkgray>|</ansidarkgray>  "
            f"<ansiyellow>{safe}</ansiyellow>  "
            f"<ansidarkgray>|  Tab: complete  |  Up/Down: history  |  /help: commands</ansidarkgray>"
        )

    def _print_header(self):
        """Renders the full KURO startup screen: cat logo + title + status."""
        self.console.clear()

        cat_panel = Panel(
            CAT_LOGO.strip(),
            border_style="cyan",
            title="[bold cyan]KURO[/]",
            padding=(0, 1),
        )
        title_text = Text.assemble(
            "\n",
            ("  KURO ", "bold cyan"),
            ("v2.0\n", "dim"),
            ("  Autonomous Terminal Intelligence\n\n", "bold white"),
            ("  Your local AI system assistant.\n", "dim"),
            ("  Trading  |  Coding  |  Research  |  System Ops\n", "dim"),
        )
        title_panel = Panel(title_text, border_style="bright_black", padding=(0, 2))

        self.console.print(Columns([cat_panel, title_panel], equal=False, expand=False))
        self.print_status_banner()
        self.console.print(
            Rule(
                "[dim]Tab autocomplete  |  /help commands  |  Ctrl+L clear  |  exit to quit[/dim]",
                style="bright_black",
            )
        )
        self.console.print()

    def print_status_banner(self):
        """Compact, inline status bar showing provider, model, key count, safe mode."""
        provider = config.get_active_provider()
        model = config.get_active_model(provider)
        pool = config.KEY_POOLS.get(provider)
        key_count = len(pool.keys) if pool else 0
        safe = "[green]SAFE[/green]" if config.SAFE_MODE else "[red]UNSAFE[/red]"
        git = "[green]GIT-ON[/green]" if config.AUTO_GIT_CHECKPOINTS else "[dim]GIT-OFF[/dim]"

        status_text = (
            f" [bold cyan]{provider.upper()}[/]  [dim]|[/]  "
            f"[yellow]{model}[/]  [dim]|[/]  "
            f"[magenta]{key_count} key(s)[/]  [dim]|[/]  "
            f"{safe}  [dim]|[/]  {git}"
        )
        self.console.print(Panel(status_text, border_style="bright_black", padding=(0, 1)))

    def display_help(self):
        """Sectioned, modern styled help panel showing only commands available in the Tab menu."""
        sections = [
            ("⚙️  System & Configuration", [
                ("/status",      "Show active LLM provider, model, & safe mode status", "Type [cyan]/status[/cyan]"),
                ("/system",      "Live PC hardware telemetry (CPU, RAM, Disk, OS)",     "Type [cyan]/system[/cyan]"),
                ("/top",         "List active running processes & memory footprint",    "[cyan]/top[/cyan] or [cyan]/top 20[/cyan]"),
                ("/safe",        "Toggle Safe Mode & permission prompts (on/off/allow)", "[cyan]/safe off[/cyan] | [cyan]/safe allow execute_python[/cyan]"),
                ("/pool",        "View API key pool rotation & rate limit cooldowns",    "Type [cyan]/pool[/cyan]"),
                ("/models",      "View model fallback chain for active provider",       "Type [cyan]/models[/cyan]"),
                ("/key",         "Add API key to provider pool & persist to .env",       "[cyan]/key <KEY>[/cyan] or [cyan]/key groq <KEY>[/cyan]"),
                ("/undo",        "Rollback last automated file changes via Git",        "Type [cyan]/undo[/cyan]"),
                ("!<cmd>",       "Direct shell command bypass (executes locally)",      "[cyan]!git status[/cyan] or [cyan]!dir[/cyan]"),
            ]),
            ("🧩  KuroHub & Capabilities", [
                ("/hub",         "Browse KuroHub capabilities (Tools, Plugins, Skills, Integrations)", "[cyan]/hub[/cyan] | [cyan]/hub list all[/cyan]"),
                ("/store",       "Alias for KuroHub capability store",                  "[cyan]/store search <query>[/cyan] | [cyan]/store install <name>[/cyan]"),
                ("/skills",      "List all installed & self-learned procedural skills",  "Type [cyan]/skills[/cyan]"),
                ("/<skill> [p]", "Directly run an installed skill with custom prompt",   "[cyan]/<skill-name> <instructions>[/cyan]"),
                ("/plugin",      "Manage plugins (install as folder, list, remove)",    "[cyan]/plugin list[/cyan] | [cyan]/plugin install <src>[/cyan]"),
                ("/integrations","Manage connected services (GitHub, Telegram, Discord)","[cyan]/integrations[/cyan] | [cyan]/integrations connect <service> <token>[/cyan]"),
            ]),
            ("🧠  Memory, Vault & Session", [
                ("/vault",       "Encrypted credential vault manager (DPAPI / AES-256)", "[cyan]/vault list[/cyan] | [cyan]/vault set <K> <V>[/cyan]"),
                ("/memory",      "Inspect persistent conversation memory and summary",  "Type [cyan]/memory[/cyan]"),
                ("/clear",       "Reset active conversation working memory",            "Type [cyan]/clear[/cyan]"),
                ("/help",        "Display this categorized command reference",          "Type [cyan]/help[/cyan]"),
                ("exit / quit",  "Terminate active KURO session",                       "Type [cyan]exit[/cyan] or [cyan]quit[/cyan]"),
            ]),
        ]

        self.console.print()
        self.console.print(
            Rule("[bold cyan]KURO 2.0  Command Reference (Tab Menu)[/bold cyan]", style="cyan")
        )
        self.console.print()

        for sec_title, cmd_rows in sections:
            table = Table(
                title=sec_title,
                title_style="bold magenta",
                border_style="cyan",
                box=box.ROUNDED,
                show_lines=False,
                header_style="bold cyan",
                expand=True,
            )
            table.add_column("Command", style="bold cyan", width=18)
            table.add_column("Capability & Action", style="white", ratio=3)
            table.add_column("How to Use / Example", style="yellow", ratio=3)

            for cmd_name, desc, usage in cmd_rows:
                table.add_row(cmd_name, desc, usage)

            self.console.print(table)
            self.console.print()

        self.console.print(
            Panel(
                "[dim]💡 Shortcuts & Tips:\n"
                "• [bold]Tab Completion:[/bold] Press [bold]Tab[/bold] to autocomplete slash commands, installed skills (e.g. /skill-name), and paths.\n"
                "• [bold]Direct Skill Execution:[/bold] Type [bold]/<skill-name> [prompt][/bold] to execute any installed procedural skill with LLM guidance.\n"
                "• [bold]KuroHub Store:[/bold] Use [bold]/hub[/bold] or [bold]/store[/bold] to install tools (.py file) or plugins & skills (folders).\n"
                "• [bold]Autonomous Tools:[/bold] File operations, search, browsing, planning, and coding are handled autonomously by Kuro.\n"
                "• [bold]Command History:[/bold] Press [bold]Up / Down arrows[/bold] to navigate previous commands.\n"
                "• [bold]Clear Terminal Screen:[/bold] Press [bold]Ctrl+L[/bold] to clear the view without losing conversation memory.[/dim]",
                title="Interactive CLI Tips",
                border_style="bright_black",
                padding=(0, 2),
            )
        )
        self.console.print()

    def display_pool_status(self):
        """Rich table of all key pools and their cooldown state."""
        summaries = config.get_pool_status_summary()
        table = Table(
            title="KURO  Resource Pool Status",
            border_style="cyan",
            box=box.ROUNDED,
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Provider", style="bold cyan", min_width=12)
        table.add_column("Keys", style="white", justify="center")
        table.add_column("Active", style="bold green", justify="center")
        table.add_column("Cooling (429)", style="red", justify="center")
        table.add_column("Model Fallback Chain", style="yellow", min_width=40)

        for s in summaries:
            models_str = " -> ".join(s["models"][:3])
            if len(s["models"]) > 3:
                models_str += f"  [dim](+{len(s['models'])-3} more)[/dim]"
            table.add_row(
                s["provider"],
                str(s["total_keys"]),
                str(s["active_keys"]),
                str(s["cooling_keys"]),
                models_str,
            )
        self.console.print()
        self.console.print(table)
        self.console.print()

    def _print_shell_output(self, cmd: str, res: dict):
        """Renders shell command output in styled panels."""
        self.console.print(f"\n[bold yellow]$ {cmd}[/]")
        if res.get("stdout"):
            self.console.print(Panel(
                res["stdout"].strip(),
                title="[bold green]stdout[/]",
                border_style="green",
                padding=(0, 1),
            ))
        if res.get("stderr"):
            self.console.print(Panel(
                res["stderr"].strip(),
                title="[bold red]stderr[/]",
                border_style="red",
                padding=(0, 1),
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # Response rendering
    # ─────────────────────────────────────────────────────────────────────────
    def print_kuro_response(self, response: str):
        """
        Renders KURO's final answer as a clean Rich Markdown panel.
        Voice (if enabled) plays in a background thread simultaneously.
        """
        # Clear the last progress/spinner line
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

        self.console.print()

        # Render response as Markdown inside a clean panel
        from rich.markdown import Markdown as _Markdown
        md = _Markdown(response, code_theme="monokai", hyperlinks=True)
        self.console.print(
            Panel(
                md,
                border_style="cyan",
                title="[bold cyan]KURO[/bold cyan]",
                title_align="left",
                padding=(1, 2),
            )
        )
        self.console.print()

    # ─────────────────────────────────────────────────────────────────────────
    # Spinner helper
    # ─────────────────────────────────────────────────────────────────────────
    def run_with_spinner(self, fn, *args, **kwargs):
        """Runs fn(*args, **kwargs) with a Rich animated spinner; returns result."""
        result_holder = [None]
        error_holder = [None]

        def _worker():
            try:
                result_holder[0] = fn(*args, **kwargs)
            except Exception as exc:
                error_holder[0] = exc

        thread = threading.Thread(target=_worker)
        thread.start()

        with Live(
            Spinner("dots2", text="[dim]Working...[/dim]"),
            console=self.console,
            refresh_per_second=12,
            transient=True,
        ):
            thread.join()

        if error_holder[0]:
            raise error_holder[0]
        return result_holder[0]

    # ─────────────────────────────────────────────────────────────────────────
    # Slash command handlers (extracted for readability)
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_slash_command(self, user_input: str, agent: KuroAgent) -> bool:
        """
        Processes a slash command string.
        Returns True if the REPL should `continue` (i.e. skip agent dispatch).
        Returns False only for /listen when speech succeeded and we want to fall
        through to agent dispatch with the captured voice text stored in the
        return value — in that case the method updates user_input via side-effect,
        but since strings are immutable we return the new input as a second value.

        Returns: (continue_repl: bool, new_user_input: str)
        """
        parts = user_input.split()
        cmd = parts[0].lower()

        # ── /help ────────────────────────────────────────────────────────────
        if cmd in ("/help", "/h", "help", "?"):
            self.display_help()

        # ── /status ──────────────────────────────────────────────────────────
        elif cmd == "/status":
            self.console.print()
            self.print_status_banner()

        # ── /system ──────────────────────────────────────────────────────────
        elif cmd == "/system":
            telemetry = get_system_telemetry()
            table = Table(
                title="[bold cyan]PC Hardware & System Telemetry[/]",
                border_style="cyan",
                box=box.ROUNDED,
                expand=True,
            )
            table.add_column("Component", style="bold cyan", width=18)
            table.add_column("Live Metric / Usage", style="yellow")
            
            ram = telemetry.get("ram", {})
            disk = telemetry.get("disk", {})
            
            table.add_row("Operating System", f"{telemetry.get('os')} {telemetry.get('release')} ({telemetry.get('user')})")
            table.add_row("CPU Cores", f"{telemetry.get('cpu_count')} logical cores")
            table.add_row("RAM Memory", f"{ram.get('used_gb', 0)} GB / {ram.get('total_gb', 0)} GB ({ram.get('percent_used', 0)}% utilized)")
            table.add_row("Primary Storage", f"{disk.get('used_gb', 0)} GB / {disk.get('total_gb', 0)} GB ({disk.get('percent_used', 0)}% utilized, {disk.get('free_gb', 0)} GB free)")
            
            self.console.print()
            self.console.print(table)
            self.console.print()

        # ── /top ─────────────────────────────────────────────────────────────
        elif cmd == "/top":
            limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 15
            procs = get_running_processes(limit=limit)
            table = Table(
                title=f"[bold cyan]Active Running Processes (Top {limit})[/]",
                border_style="cyan",
                box=box.ROUNDED,
                expand=True,
            )
            table.add_column("Process Name", style="bold cyan")
            table.add_column("PID", style="yellow", justify="right")
            table.add_column("Session", style="dim")
            table.add_column("Memory", style="green", justify="right")
            
            for p in procs:
                table.add_row(p.get("name", "?"), str(p.get("pid", "?")), p.get("session", "?"), p.get("memory", "?"))
            
            self.console.print()
            self.console.print(table)
            self.console.print()

        # ── /screen ──────────────────────────────────────────────────────────
        elif cmd == "/screen":
            self.console.print("[cyan]Capturing primary screen...[/]")
            res = capture_screen()
            if res.get("success"):
                self.console.print(f"[bold green]  [OK] Screenshot saved to:[/] {res.get('path')}")
            else:
                self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

        # ── /open ────────────────────────────────────────────────────────────
        elif cmd == "/open":
            if len(parts) < 2:
                self.console.print("[yellow]  Usage: /open <app_name | file_path | url>[/]")
            else:
                target = " ".join(parts[1:])
                res = open_app_or_file(target)
                if res.get("success"):
                    self.console.print(f"[bold green]  [OK] Launched:[/] {target}")
                else:
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")


        # ── /pool ────────────────────────────────────────────────────────────
        elif cmd == "/pool":
            self.display_pool_status()

        # ── /models ──────────────────────────────────────────────────────────
        elif cmd == "/models":
            target_prov = parts[1].lower() if len(parts) > 1 else None
            active_prov = config.get_active_provider()
            
            if target_prov:
                # Show specific provider's models
                chain = config.MODEL_CHAINS.get(target_prov, [])
                if not chain:
                    self.console.print(f"[bold red]Unknown provider:[/] {target_prov}")
                    self.console.print(f"[dim]Available providers: {', '.join(config.PROVIDER_CHAIN)}[/]")
                else:
                    self.console.print()
                    table = Table(
                        title=f"Models for {target_prov.upper()}",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                    table.add_column("Priority", justify="center", style="dim")
                    table.add_column("Model", style="yellow")
                    for i, m in enumerate(chain, 1):
                        is_active = (target_prov == active_prov and i == 1)
                        badge = "[bold green](active)[/]" if is_active else ""
                        table.add_row(str(i), f"{m}  {badge}")
                    self.console.print(table)
                    self.console.print()
            else:
                # Show active provider chain + all registered providers overview
                chain = config.MODEL_CHAINS.get(active_prov, [])
                self.console.print()
                table = Table(
                    title=f"Active Provider: [bold green]{active_prov.upper()}[/] (Fallback Chain)",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
                table.add_column("Priority", justify="center", style="dim")
                table.add_column("Model", style="yellow")
                for i, m in enumerate(chain, 1):
                    badge = "[bold green](active)[/]" if i == 1 else ""
                    table.add_row(str(i), f"{m}  {badge}")
                self.console.print(table)

                # Summary of all 9 providers
                summary_table = Table(
                    title="All Registered Providers (from models.json)",
                    border_style="dim cyan",
                    box=box.SIMPLE,
                )
                summary_table.add_column("Provider", style="bold")
                summary_table.add_column("Default Model", style="yellow")
                summary_table.add_column("Total Models", justify="center", style="dim")
                summary_table.add_column("Status", justify="center")

                available_set = set(config.get_available_providers())
                for prov in config.PROVIDER_CHAIN:
                    models = config.MODEL_CHAINS.get(prov, [])
                    is_active = (prov == active_prov)
                    has_key = (prov in available_set)
                    status = "[bold green]ACTIVE[/]" if is_active else ("[green]READY[/]" if has_key else "[dim red]NO KEY[/]")
                    summary_table.add_row(
                        prov.upper(),
                        models[0] if models else "N/A",
                        str(len(models)),
                        status
                    )
                self.console.print(summary_table)
                self.console.print("[dim]Tip: Switch active provider by setting KURO_PROVIDER=<name> in .env or your environment.[/]")
                self.console.print("[dim]     View a specific provider: /models <gemini|groq|openrouter|mistral|cloudflare|openai|anthropic|deepseek|xai>[/]\n")


        # ── /undo ────────────────────────────────────────────────────────────
        elif cmd == "/undo":
            self.console.print("[bold yellow]Rolling back last file changes...[/]")
            res = rollback_checkpoint()
            if res.get("success"):
                self.console.print(f"[bold green]  [OK] {res.get('stdout')}[/]")
            else:
                self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

        # ── /search ──────────────────────────────────────────────────────────
        elif cmd == "/search":
            if len(parts) < 2:
                self.console.print("[yellow]  Usage: /search <query>[/]")
            else:
                q = " ".join(parts[1:])
                self.console.print(f"[bold yellow]  Searching:[/] {q}")
                res = search_web(q)
                results = res.get("results", [])
                table = Table(
                    border_style="cyan", box=box.SIMPLE, show_header=False, padding=(0, 1)
                )
                table.add_column("", style="dim")
                table.add_column("", style="white")
                for i, r in enumerate(results[:5], 1):
                    table.add_row(
                        f"[cyan]{i}.[/]",
                        f"[white]{r.get('snippet', '')}[/]\n[dim]{r.get('url', '')}[/]",
                    )
                self.console.print(Panel(table, title=f"Web Search: {q}", border_style="cyan"))

        # ── /clear ───────────────────────────────────────────────────────────
        elif cmd == "/clear":
            memory.clear_memory()
            self.console.print("[bold green]  Memory cleared.[/]")

        # ── /memory ──────────────────────────────────────────────────────────
        elif cmd == "/memory":
            items = memory.load_memory()
            if not items:
                self.console.print("[yellow]  Memory is empty.[/]")
            else:
                for i, item in enumerate(items[-5:], 1):
                    self.console.print(Panel(
                        f"[bold cyan]You:[/] {item.get('user', '')}\n"
                        f"[bold white]KURO:[/] {item.get('assistant', '')[:300]}...",
                        title=f"Memory [{i}]",
                        border_style="bright_black",
                    ))


        # ── /see ─────────────────────────────────────────────────────────────
        elif cmd == "/see":
            if len(parts) < 2:
                self.console.print("[yellow]  Usage: /see <image_path> [prompt][/]")
            else:
                from kurocode.tools.vision import analyze_image_tool
                img_path = parts[1]
                prompt_text = (
                    " ".join(parts[2:]) if len(parts) > 2
                    else "Describe this image in detail and extract key information."
                )
                self.console.print(f"[bold cyan]  Analyzing Image:[/] {img_path}")
                res = analyze_image_tool(img_path, prompt_text)
                if not res.get("success"):
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
                else:
                    with Live(
                        Spinner("dots", text="[bold cyan]KURO Vision analyzing...[/]"),
                        refresh_per_second=12,
                        console=self.console,
                    ):
                        vision_res = ask_llm(
                            prompt_text,
                            system_prompt="You are KURO Vision. Analyze the image accurately.",
                            provider=agent.provider,
                            model=agent.model,
                            image_info=res,
                        )
                    self.print_kuro_response(vision_res)

        # ── /browse ──────────────────────────────────────────────────────────
        elif cmd == "/browse":
            if len(parts) < 2:
                self.console.print("[yellow]  Usage: /browse <url>[/]")
            else:
                from kurocode.tools.browser import browse_web_headless
                url_target = parts[1]
                self.console.print(f"[bold yellow]  Headless Browsing:[/] {url_target}")
                res = browse_web_headless(url_target)
                if not res.get("success"):
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
                else:
                    self.console.print(Panel(
                        f"[bold cyan]Title:[/] {res.get('title')}\n\n"
                        f"[bold white]Content Preview (Word Count: {res.get('word_count')}):[/]\n"
                        f"{res.get('content_preview', '')[:1500]}...",
                        title=f"Headless Browser: {url_target}",
                        border_style="cyan",
                    ))

        # ── /learn ───────────────────────────────────────────────────────────
        elif cmd == "/learn":
            if len(parts) < 3:
                self.console.print("[yellow]  Usage: /learn <skill_name> <steps / description>[/]")
            else:
                s_name = parts[1]
                s_steps = " ".join(parts[2:])
                res = save_learned_skill(s_name, f"Custom user routine: {s_name}", s_steps)
                if res.get("success"):
                    self.console.print(
                        f"[bold green]  [OK] Skill '{s_name}' learned and saved to scratch/skills![/]"
                    )
                else:
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

        # ── /skills ──────────────────────────────────────────────────────────
        elif cmd == "/skills":
            skills = list_learned_skills()
            if not skills:
                self.console.print(
                    "[yellow]  No custom learned skills saved yet. Use /learn <name> <steps> to add one![/]"
                )
            else:
                table = Table(
                    title="KURO Self-Learned Skills", border_style="cyan", box=box.ROUNDED
                )
                table.add_column("Skill Name", style="bold cyan")
                table.add_column("Location", style="dim")
                table.add_column("Preview", style="white")
                for s in skills:
                    table.add_row(s["name"], s["path"], s["preview"][:80] + "...")
                self.console.print(table)

        # ── /key ─────────────────────────────────────────────────────────────
        elif cmd == "/key":
            if len(parts) == 2:
                target_key, target_prov = parts[1], "gemini"
            elif len(parts) >= 3:
                target_prov, target_key = parts[1].lower(), parts[2]
            else:
                self.console.print("[yellow]  Usage: /key <KEY>  or  /key <provider> <KEY>[/]")
                return True, user_input

            if config.save_api_key(target_key, target_prov):
                agent.provider = config.get_active_provider()
                agent.model    = config.get_active_model(agent.provider)
                self.console.print(f"[bold green]  [OK] Key added to {target_prov.upper()} pool & saved.[/]")
                self.console.print()
                self.print_status_banner()
            else:
                self.console.print("[bold red]  [FAIL] Could not save API key.[/]")

        # ── /plan ────────────────────────────────────────────────────────────
        elif cmd == "/plan":
            if len(parts) < 2:
                active = get_active_plan()
                if active:
                    self.console.print(
                        Panel(format_plan_table(active), border_style="magenta", title="Active Task Plan")
                    )
                else:
                    self.console.print("[yellow]  Usage: /plan <goal_description>[/]")
            else:
                goal_text = " ".join(parts[1:])
                self.console.print(f"[bold magenta]  Generating Task Plan:[/] {goal_text}")
                plan = create_task_plan(goal_text, llm_fn=ask_llm)
                self.console.print(
                    Panel(format_plan_table(plan), border_style="magenta", title="Generated Task Plan")
                )

        # ── /sql ─────────────────────────────────────────────────────────────
        elif cmd == "/sql":
            if len(parts) < 2:
                self.console.print(
                    "[yellow]  Usage: /sql <query_or_script>  (runs against the KURO brain database)[/]"
                )
            else:
                q = " ".join(parts[1:])
                res = execute_sql_query(str(DB_PATH), q)
                if res.get("success"):
                    rows = res.get("rows", [])
                    if rows:
                        table = Table(title="SQL Query Result", border_style="cyan", box=box.ROUNDED)
                        for col in rows[0].keys():
                            table.add_column(col, style="yellow")
                        for r in rows[:10]:
                            table.add_row(*[str(v) for v in r.values()])
                        self.console.print(table)
                    else:
                        self.console.print(
                            f"[bold green]  [OK] {res.get('message', 'Query executed successfully.')}[/]"
                        )
                else:
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

        # ── /notes ───────────────────────────────────────────────────────────
        elif cmd == "/notes":
            if len(parts) < 3:
                self.console.print("[yellow]  Usage: /notes <filename.md> <content>[/]")
            else:
                fname = parts[1]
                if not fname.endswith(".md"):
                    fname += ".md"
                note_body = " ".join(parts[2:])
                res = write_md_note(str(NOTES_DIR / fname), fname, note_body)
                if res.get("success"):
                    self.console.print(f"[bold green]  [OK] Note saved to {NOTES_DIR / fname}[/]")
                else:
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

        # ── /notify ──────────────────────────────────────────────────────────
        elif cmd == "/notify":
            if len(parts) < 2:
                self.console.print(Panel(
                    "[bold cyan]KURO Notification Engine — Discord & Telegram[/]\n\n"
                    "• [bold]Basic:[/bold]        [cyan]/notify <message>[/cyan]\n"
                    "• [bold]Titled:[/bold]       [cyan]/notify <title> | <message>[/cyan]\n"
                    "• [bold]To Telegram:[/bold]  [cyan]/notify --channel telegram [--target @channel_name] <message>[/cyan]\n"
                    "• [bold]To Discord:[/bold]   [cyan]/notify --channel discord <message>[/cyan]\n"
                    "• [bold]With Image:[/bold]   [cyan]/notify --image C:\\image.png --channel telegram <caption>[/cyan]\n"
                    "• [bold]Urgency:[/bold]      [cyan]/notify --priority <info|success|warning|critical|alert> <message>[/cyan]\n\n"
                    "[bold yellow]Channel Configuration & Diagnostics:[/bold yellow]\n"
                    "  - [cyan]/notify config telegram <BOT_TOKEN> <CHAT_ID_OR_CHANNEL>[/cyan]\n"
                    "  - [cyan]/notify config discord <WEBHOOK_URL>[/cyan]\n"
                    "  - [cyan]/notify test [telegram|discord|all][/cyan]\n"
                    "  - [cyan]/notify diagnose telegram [@channel_or_chat_id][/cyan]",
                    title="🔔 Notification Engine",
                    border_style="cyan",
                ))
            else:
                from kurocode.tools.notifier import (
                    send_smart_notification,
                    load_notification_config,
                    save_notification_config,
                    diagnose_channel,
                    NotificationUrgency,
                )
                subcmd = parts[1].lower()

                if subcmd == "test":
                    target_ch = parts[2].lower() if len(parts) > 2 else "all"
                    self.console.print(
                        f"[bold cyan]  Running diagnostic test on channel:[/] [yellow]{target_ch.upper()}[/]"
                    )
                    res = send_smart_notification(
                        title="System Test Alert",
                        message="KURO 2.0 notification engine is operational and verified!",
                        urgency=NotificationUrgency.SUCCESS,
                        channels=[target_ch],
                        speak=target_ch in ("toast", "all"),
                    )
                    table = Table(
                        title="Notification Dispatch Report", border_style="cyan", box=box.ROUNDED
                    )
                    table.add_column("Channel", style="bold cyan")
                    table.add_column("Status", justify="center")
                    table.add_column("Details / Diagnosis", style="yellow")
                    for ch, ch_res in res.get("dispatched", {}).items():
                        ok = ch_res.get("success", False)
                        status_str = "[bold green]✓ SUCCESS[/]" if ok else "[bold red]✗ FAILED[/]"
                        detail = str(ch_res.get("error") or ch_res.get("message") or "Delivered successfully")
                        table.add_row(ch.upper(), status_str, detail)
                    self.console.print(table)

                elif subcmd == "diagnose":
                    target_ch = parts[2].lower() if len(parts) > 2 else "telegram"
                    target_id = parts[3] if len(parts) > 3 else None
                    self.console.print(
                        f"[bold cyan]  Diagnosing channel:[/] [yellow]{target_ch.upper()}[/]"
                    )
                    diag = diagnose_channel(target_ch, target=target_id)
                    self.console.print(Panel(
                        json.dumps(diag, indent=2, ensure_ascii=False),
                        title=f"Channel Diagnostic: {target_ch.upper()}",
                        border_style="cyan",
                    ))

                elif subcmd == "config":
                    if len(parts) < 4:
                        self.console.print(
                            "[yellow]  Usage: /notify config <discord|telegram> <TOKEN_OR_URL> [CHAT_ID_OR_CHANNEL][/]"
                        )
                    else:
                        target_chan = parts[2].lower()
                        cfg = load_notification_config()
                        if target_chan in ("discord", "disc"):
                            cfg["discord_webhook"] = parts[3]
                            save_notification_config(cfg)
                            self.console.print(
                                "[bold green]  [OK] Discord webhook configured & stored in Encrypted Vault![/]"
                            )
                        elif target_chan in ("telegram", "tg"):
                            cfg["telegram_token"] = parts[3]
                            if len(parts) > 4:
                                cfg["telegram_chat_id"] = parts[4]
                            save_notification_config(cfg)
                            self.console.print(
                                f"[bold green]  [OK] Telegram configured! (Chat/Channel: {cfg.get('telegram_chat_id', 'Default')})[/]"
                            )
                        else:
                            self.console.print(f"[yellow]  Unknown channel '{target_chan}'. Use: discord, telegram[/]")


                else:
                    # Parse flags: --priority, --sound, --speak, --channel, --target, --image
                    raw_args = parts[1:]
                    urgency = NotificationUrgency.INFO
                    sound_preset = "default"
                    speak_alert = False
                    chan_override = None
                    target_override = None
                    image_path = None
                    clean_parts = []
                    i = 0
                    while i < len(raw_args):
                        arg = raw_args[i]
                        if arg in ("--priority", "-p") and i + 1 < len(raw_args):
                            try:
                                urgency = NotificationUrgency(raw_args[i + 1].lower())
                            except Exception:
                                pass
                            i += 2
                        elif arg in ("--sound", "-s") and i + 1 < len(raw_args):
                            sound_preset = raw_args[i + 1].lower()
                            i += 2
                        elif arg in ("--speak", "-v"):
                            speak_alert = True
                            i += 1
                        elif arg in ("--channel", "-c") and i + 1 < len(raw_args):
                            chan_override = [raw_args[i + 1].lower()]
                            i += 2
                        elif arg in ("--target", "-t") and i + 1 < len(raw_args):
                            target_override = raw_args[i + 1]
                            i += 2
                        elif arg in ("--image", "-i") and i + 1 < len(raw_args):
                            image_path = raw_args[i + 1]
                            i += 2
                        else:
                            clean_parts.append(arg)
                            i += 1

                    full_txt = " ".join(clean_parts)
                    if "|" in full_txt:
                        ntitle, nmsg = [p.strip() for p in full_txt.split("|", 1)]
                    else:
                        ntitle, nmsg = "KURO System Assistant", full_txt

                    res = send_smart_notification(
                        title=ntitle,
                        message=nmsg,
                        urgency=urgency,
                        channels=chan_override,
                        speak=speak_alert,
                        sound=sound_preset,
                        target_override=target_override,
                        image_path=image_path,
                    )
                    if res.get("success"):
                        self.console.print(
                            f"[bold green]  [OK] Notification sent ({urgency.value.upper()})! "
                            f"Dispatched to: {list(res.get('dispatched', {}).keys())}[/]"
                        )
                    else:
                        err_details = [
                            f"{k_ch.upper()}: {v_ch.get('error', 'Failed')}"
                            for k_ch, v_ch in res.get("dispatched", {}).items()
                            if not v_ch.get("success")
                        ]
                        self.console.print(
                            f"[bold red]  [FAIL] Notification error:[/] "
                            f"{'; '.join(err_details) if err_details else 'Failed to deliver'}"
                        )


        # ── /dir ─────────────────────────────────────────────────────────────
        elif cmd == "/dir":
            target_path = parts[1] if len(parts) > 1 else "."
            from kurocode.tools.files import list_directory
            res = list_directory(target_path)
            if res.get("success"):
                table = Table(
                    title=f"Directory Listing: {target_path}",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
                table.add_column("Type", style="yellow", width=8)
                table.add_column("Name", style="bold cyan")
                table.add_column("Size", justify="right", style="dim")
                for item in res.get("items", []):
                    table.add_row(
                        item.get("type", "file"),
                        item.get("name", ""),
                        str(item.get("size", "-")),
                    )
                self.console.print(table)
            else:
                self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

        # ── /project ─────────────────────────────────────────────────────────
        elif cmd == "/project":
            from kurocode.core.project_aware import project_inspector
            profile = project_inspector.inspect(".", force_refresh=True)
            self.console.print(Panel(
                f"[bold cyan]Project Profile:[/] {profile.name}\n\n"
                f"[bold yellow]Languages:[/] {', '.join(profile.languages)}\n"
                f"[bold yellow]Frameworks:[/] {', '.join(profile.frameworks) if profile.frameworks else 'None'}\n"
                f"[bold yellow]Package Managers:[/] {', '.join(profile.package_managers)}\n"
                f"[bold yellow]Entry Points:[/] {', '.join(profile.entry_points)}\n"
                f"[bold yellow]Git Status:[/] {profile.git_status}\n"
                f"[bold yellow]Build Cmd:[/] `{profile.build_command}`\n"
                f"[bold yellow]Test Cmd:[/] `{profile.test_command}`",
                title="Project Profile",
                border_style="cyan",
            ))

        # ── /integrations ────────────────────────────────────────────────────
        elif cmd == "/integrations":
            from kurocode.core.integration_manager import integration_manager
            integs = integration_manager.list_integrations()
            table = Table(
                title="Connected Services & External Integrations",
                border_style="cyan",
                box=box.ROUNDED,
            )
            table.add_column("Integration", style="bold cyan")
            table.add_column("Connected", justify="center")
            table.add_column("Account / Details", style="yellow")
            for integ in integs:
                tick = "[bold green]✓ Connected[/]" if integ["connected"] else "[dim]○ Disconnected[/]"
                table.add_row(integ["name"].upper(), tick, str(integ.get("account", "-")))
            self.console.print(table)
            self.console.print(Panel(
                "[dim]How to connect an integration:\n"
                "• Connect Telegram:     [cyan]/connect telegram <BOT_TOKEN> [CHAT_ID_OR_CHANNEL][/cyan]\n"
                "• Connect Discord:      [cyan]/connect discord <WEBHOOK_URL>[/cyan]\n"
                "• Connect GitHub:       [cyan]/connect github <PERSONAL_ACCESS_TOKEN>[/cyan]\n"
                "• Connect Google Drive: [cyan]/connect drive <DRIVE_API_TOKEN>[/cyan]\n"
                "• Connect Email:        [cyan]/connect email <EMAIL_API_TOKEN>[/cyan]\n"
                "• Disconnect service:   [cyan]/disconnect <service_name>[/cyan]\n\n"
                "Tokens are encrypted and stored securely in your Encrypted Secret Vault.[/dim]",
                border_style="bright_black",
                padding=(0, 2),
            ))

        # ── /connect ─────────────────────────────────────────────────────────
        elif cmd == "/connect":
            if len(parts) < 3:
                self.console.print(
                    "[yellow]  Usage: /connect <telegram|discord|github|drive|email> <TOKEN_OR_URL> [chat_id_or_user][/]"
                )
            else:
                target_service = parts[1].lower()
                if target_service in ("drive", "gdrive", "google-drive"):
                    target_service = "google_drive"
                elif target_service in ("tg", "tele"):
                    target_service = "telegram"
                elif target_service in ("disc",):
                    target_service = "discord"

                target_token = parts[2]
                target_user = parts[3] if len(parts) > 3 else None

                from kurocode.core.integration_manager import integration_manager
                if integration_manager.connect_integration(target_service, target_token, user=target_user):
                    self.console.print(
                        f"[bold green]  [OK] Integration '{target_service.upper()}' "
                        "successfully connected and saved in Encrypted Vault![/]"
                    )
                else:
                    self.console.print(
                        f"[bold red]  [FAIL] Failed to connect integration '{target_service}'. "
                        "Verify your token/credentials.[/]"
                    )

        # ── /disconnect ──────────────────────────────────────────────────────
        elif cmd == "/disconnect":
            if len(parts) < 2:
                self.console.print(
                    "[yellow]  Usage: /disconnect <telegram|discord|github|drive|email>[/]"
                )
            else:
                target_service = parts[1].lower()
                if target_service in ("drive", "gdrive", "google-drive"):
                    target_service = "google_drive"
                elif target_service in ("tg", "tele"):
                    target_service = "telegram"
                elif target_service in ("disc",):
                    target_service = "discord"

                from kurocode.core.integration_manager import integration_manager
                if integration_manager.disconnect_integration(target_service):
                    self.console.print(
                        f"[bold green]  [OK] Integration '{target_service.upper()}' disconnected.[/]"
                    )
                else:
                    self.console.print(
                        f"[bold red]  [FAIL] Failed to disconnect integration '{target_service}'.[/]"
                    )

        # ── /tasks ───────────────────────────────────────────────────────────
        elif cmd == "/tasks":
            from kurocode.core.task_state import task_registry
            tasks = task_registry.list_all()
            if not tasks:
                self.console.print("[yellow]  No task lifecycle history recorded yet.[/]")
            else:
                table = Table(
                    title="Task Lifecycle State Machine History",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
                table.add_column("Task ID", style="bold cyan")
                table.add_column("State", style="yellow")
                table.add_column("Goal", style="white")
                for t in tasks[-10:]:
                    table.add_row(t.task_id, t.state.value.upper(), t.goal[:50])
                self.console.print(table)

        # ── /metrics ─────────────────────────────────────────────────────────
        elif cmd == "/metrics":
            from kurocode.core.memory_db import get_metrics_summary
            metrics = get_metrics_summary(limit=10)
            if not metrics:
                self.console.print("[yellow]  No execution metrics recorded yet.[/]")
            else:
                table = Table(
                    title="Execution Analytics & Metrics Summary",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
                table.add_column("Task ID", style="dim")
                table.add_column("Provider / Model", style="bold cyan")
                table.add_column("Tool Calls", justify="center", style="yellow")
                table.add_column("Duration", justify="right", style="green")
                for m in metrics:
                    table.add_row(
                        str(m.get("task_id", "N/A")),
                        f"{m.get('provider')}/{m.get('model')}",
                        str(m.get("tool_calls", 0)),
                        f"{m.get('duration_seconds', 0.0):.1f}s",
                    )
                self.console.print(table)

        # ── /vault ───────────────────────────────────────────────────────────
        elif cmd == "/vault":
            from kurocode.core.vault import vault
            subcmd = parts[1].lower() if len(parts) > 1 else "list"

            if subcmd == "status":
                status = vault.get_status()
                self.console.print(Panel(
                    f"[bold cyan]Vault Storage Path:[/] {status['path']}\n"
                    f"[bold yellow]Vault Exists:[/] {status['exists']}\n"
                    f"[bold yellow]Lock Status:[/] {'[red]LOCKED[/red]' if status['locked'] else '[green]UNLOCKED[/green]'}\n"
                    f"[bold yellow]Crypto Backend:[/] {status['backend']}\n"
                    f"[bold yellow]Total Secrets:[/] {status['secret_count']}\n"
                    f"[bold yellow]Custom Master Password:[/] {status['has_password']}",
                    title="🔒 KURO Encrypted Credential Vault Status",
                    border_style="cyan",
                ))

            elif subcmd == "list":
                secrets = vault.list_secrets()
                if not secrets:
                    self.console.print(
                        "[yellow]  Vault is empty or locked. Use /vault set <KEY> <VALUE> or /vault migrate.[/]"
                    )
                else:
                    table = Table(
                        title="🔒 KURO Encrypted Secret Vault",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                    table.add_column("Secret Key", style="bold cyan")
                    table.add_column("Encrypted / Masked Value", style="yellow")
                    table.add_column("Description", style="white")
                    for s in secrets:
                        table.add_row(s["key"], s["masked"], s["description"] or "-")
                    self.console.print(table)
                    self.console.print(Panel(
                        "[dim]• Set secret:    [cyan]/vault set <KEY> <VALUE> [description][/cyan]\n"
                        "• Get secret:    [cyan]/vault get <KEY> [--reveal][/cyan]\n"
                        "• Delete secret: [cyan]/vault delete <KEY>[/cyan]\n"
                        "• Auto-migrate:  [cyan]/vault migrate[/cyan] (imports API keys from .env)[/dim]",
                        border_style="bright_black",
                        padding=(0, 2),
                    ))

            elif subcmd == "set":
                if len(parts) < 4:
                    self.console.print("[yellow]  Usage: /vault set <KEY> <VALUE> [description][/]")
                else:
                    k = parts[2]
                    v = parts[3]
                    desc = " ".join(parts[4:]) if len(parts) > 4 else "Stored credential"
                    if vault.set_secret(k, v, description=desc):
                        self.console.print(
                            f"[bold green]  [OK] Secret '{k.upper()}' encrypted and securely stored in vault![/]"
                        )
                    else:
                        self.console.print(
                            f"[bold red]  [FAIL] Failed to save secret '{k}'. Vault may be locked.[/]"
                        )

            elif subcmd == "get":
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /vault get <KEY> [--reveal][/]")
                else:
                    k = parts[2]
                    reveal = "--reveal" in parts or "-r" in parts
                    sec = vault.get_secret(k)
                    if sec is None:
                        self.console.print(f"[yellow]  Secret '{k.upper()}' not found in vault.[/]")
                    else:
                        if reveal:
                            self.console.print(f"[bold green]  {k.upper()}:[/] [white]{sec}[/]")
                        else:
                            from kurocode.core.vault import mask_secret
                            self.console.print(
                                f"[bold green]  {k.upper()}:[/] [yellow]{mask_secret(sec)}[/] "
                                "[dim](use --reveal to display plaintext)[/dim]"
                            )

            elif subcmd == "delete":
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /vault delete <KEY>[/]")
                else:
                    k = parts[2]
                    if vault.delete_secret(k):
                        self.console.print(f"[bold green]  [OK] Secret '{k.upper()}' deleted from vault.[/]")
                    else:
                        self.console.print(
                            f"[bold red]  [FAIL] Secret '{k.upper()}' not found or vault is locked.[/]"
                        )

            elif subcmd == "migrate":
                count = vault.auto_migrate_from_env()
                self.console.print(
                    f"[bold green]  [OK] Migrated {count} secret(s) from .env into encrypted vault![/]"
                )

            elif subcmd == "lock":
                vault.lock()
                self.console.print("[bold yellow]  [LOCKED] Vault locked and in-memory secrets purged.[/]")

            elif subcmd == "unlock":
                pwd = parts[2] if len(parts) > 2 else None
                if vault.unlock(password=pwd):
                    self.console.print("[bold green]  [OK] Vault unlocked successfully![/]")
                else:
                    self.console.print(
                        "[bold red]  [FAIL] Failed to unlock vault. Incorrect password or decryption error.[/]"
                    )

            else:
                self.console.print("[yellow]  Usage: /vault <list|status|set|get|delete|migrate|lock|unlock>[/]")

        # ── /sandbox ─────────────────────────────────────────────────────────
        elif cmd == "/sandbox":
            from pathlib import Path
            from kurocode.core.sandbox import sandbox
            subcmd = parts[1].lower() if len(parts) > 1 else "status"

            if subcmd in ("status", "info"):
                status = sandbox.get_status()
                self.console.print(Panel(
                    f"[bold yellow]Sandbox Guard Active:[/] "
                    f"{'[bold green]ENABLED[/bold green]' if status['enabled'] else '[bold red]DISABLED[/bold red]'}\n"
                    f"[bold yellow]Strict AST Mode:[/] {status['strict_mode']}\n"
                    f"[bold yellow]Privacy PII Masking:[/] {status['privacy_masking']}\n"
                    f"[bold yellow]Sandbox Workspace:[/] {status['sandbox_dir']}\n"
                    f"[bold yellow]Temp Sandbox Files:[/] {status['total_sandbox_files']}",
                    title="🛡️ KURO Sandbox Guard & Safety Engine",
                    border_style="cyan",
                ))

            elif subcmd in ("on", "enable"):
                sandbox.enable()
                self.console.print("[bold green]  [OK] Sandbox execution guardrail ENABLED.[/]")

            elif subcmd in ("off", "disable"):
                sandbox.disable()
                self.console.print("[bold yellow]  [WARNING] Sandbox execution guardrail DISABLED.[/]")

            elif subcmd == "toggle":
                new_state = sandbox.toggle()
                state_str = "[bold green]ENABLED[/bold green]" if new_state else "[bold red]DISABLED[/bold red]"
                self.console.print(f"  [OK] Sandbox guard is now {state_str}.")

            elif subcmd == "clean":
                cleaned = sandbox.clean_sandbox()
                self.console.print(
                    f"[bold green]  [OK] Cleaned {cleaned} temporary files from sandbox workspace.[/]"
                )

            elif subcmd == "check":
                if len(parts) < 3:
                    self.console.print(
                        "[yellow]  Usage: /sandbox check <python_code_or_file_path>[/]"
                    )
                else:
                    target = " ".join(parts[2:])
                    if Path(target).exists() and Path(target).is_file():
                        code_to_check = Path(target).read_text(encoding="utf-8")
                    else:
                        code_to_check = target
                    rep = sandbox.validate_python_code(code_to_check)
                    table = Table(
                        title="AST Code Safety Inspection", border_style="cyan", box=box.ROUNDED
                    )
                    table.add_column("Property", style="bold cyan")
                    table.add_column("Value", style="yellow")
                    table.add_row("Is Safe", str(rep.is_safe))
                    table.add_row("Risk Level", rep.risk_level)
                    table.add_row("Violations", "\n".join(rep.violations) if rep.violations else "None")
                    table.add_row("Warnings", "\n".join(rep.warnings) if rep.warnings else "None")
                    self.console.print(table)

            else:
                self.console.print("[yellow]  Usage: /sandbox <status|on|off|toggle|clean|check>[/]")

        # ── /safe ────────────────────────────────────────────────────────────
        elif cmd == "/safe":
            from kurocode.core.permissions import default_gate
            subcmd = parts[1].lower() if len(parts) > 1 else "status"

            if subcmd in ("status", "info"):
                status_str = (
                    "[bold green]ENABLED (Prompt for impactful actions)[/bold green]"
                    if config.SAFE_MODE
                    else "[bold yellow]DISABLED (Auto-allow confirmable actions)[/bold yellow]"
                )
                overrides = list(default_gate._overrides.keys())
                overrides_str = ", ".join(overrides) if overrides else "None"
                self.console.print(Panel(
                    f"[bold cyan]Safe Mode Status:[/] {status_str}\n"
                    f"[bold yellow]Tool Overrides (Always Allowed):[/] {overrides_str}\n\n"
                    "[dim]• Enable Safe Mode:      [cyan]/safe on[/cyan]\n"
                    "• Disable Safe Mode:     [cyan]/safe off[/cyan]\n"
                    "• Toggle:                [cyan]/safe toggle[/cyan]\n"
                    "• Always Allow One Tool: [cyan]/safe allow <action_name>[/cyan] (e.g. /safe allow execute_python)\n"
                    "• Clear Overrides:       [cyan]/safe clear[/cyan][/dim]",
                    title="🛡️ KURO Permission Gate & Safe Mode",
                    border_style="cyan",
                ))

            elif subcmd in ("on", "enable"):
                config.SAFE_MODE = True
                default_gate.set_safe_mode(True)
                self.console.print(
                    "[bold green]  [OK] Safe Mode ENABLED. Impactful actions will prompt for confirmation.[/]"
                )

            elif subcmd in ("off", "disable"):
                config.SAFE_MODE = False
                default_gate.set_safe_mode(False)
                self.console.print(
                    "[bold yellow]  [WARNING] Safe Mode DISABLED. Autonomous tools "
                    "(Python, file writes, commands) will execute without prompting.[/]"
                )

            elif subcmd == "toggle":
                config.SAFE_MODE = not config.SAFE_MODE
                default_gate.set_safe_mode(config.SAFE_MODE)
                state_str = "[bold green]ENABLED[/bold green]" if config.SAFE_MODE else "[bold yellow]DISABLED[/bold yellow]"
                self.console.print(f"  [OK] Safe Mode is now {state_str}.")

            elif subcmd == "allow":
                if len(parts) < 3:
                    self.console.print(
                        "[yellow]  Usage: /safe allow <action_name>  (e.g. /safe allow execute_python)[/]"
                    )
                else:
                    target_tool = parts[2]
                    default_gate.allow_action(target_tool)
                    self.console.print(
                        f"[bold green]  [OK] Tool '{target_tool}' will now always be permitted without confirmation prompts.[/]"
                    )

            elif subcmd in ("clear", "reset"):
                default_gate.clear_overrides()
                self.console.print("[bold green]  [OK] Cleared all tool permission overrides.[/]")

            else:
                self.console.print("[yellow]  Usage: /safe <status|on|off|toggle|allow <tool>|clear>[/]")

        # ── /plugin ──────────────────────────────────────────────────────────
        elif cmd == "/plugin":
            from kurocode.plugins.manager import plugin_manager
            subcmd = parts[1].lower() if len(parts) > 1 else "list"
            if subcmd == "list":
                plugins = plugin_manager.list_plugins()
                if not plugins:
                    self.console.print("[yellow]  No plugins installed yet.[/]")
                else:
                    table = Table(title="Installed Plugins", border_style="cyan", box=box.ROUNDED)
                    table.add_column("Plugin Name", style="bold cyan")
                    table.add_column("Version", style="green")
                    table.add_column("Status", style="yellow")
                    table.add_column("Description", style="white")
                    for p in plugins:
                        table.add_row(
                            p.get("name", "Unknown"),
                            p.get("version", "1.0.0"),
                            "Active" if p.get("enabled", True) else "Disabled",
                            p.get("description", "")
                        )
                    self.console.print(table)
            elif subcmd in ("install", "add"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /plugin install <path_or_git_url>[/]")
                else:
                    target = parts[2]
                    res = plugin_manager.install_from_source(target)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] Plugin installed successfully: {res.get('plugin')}[/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
            elif subcmd in ("remove", "uninstall", "delete"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /plugin remove <plugin_name>[/]")
                else:
                    target = parts[2]
                    res = plugin_manager.uninstall_plugin(target)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] Plugin '{target}' removed successfully.[/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
            else:
                self.console.print("[yellow]  Usage: /plugin <list|install <source>|remove <name>>[/]")

        # ── /skill ───────────────────────────────────────────────────────────
        elif cmd == "/skill":
            from kurocode.tools.self_improve import list_learned_skills, install_skill, delete_skill
            subcmd = parts[1].lower() if len(parts) > 1 else "list"
            if subcmd == "list":
                skills = list_learned_skills()
                if not skills:
                    self.console.print("[yellow]  No custom skills available.[/]")
                else:
                    table = Table(title="Available Skills", border_style="cyan", box=box.ROUNDED)
                    table.add_column("Skill Name", style="bold cyan")
                    table.add_column("Location", style="dim")
                    table.add_column("Description", style="white")
                    for s in skills:
                        table.add_row(
                            s.get("name", ""),
                            str(s.get("path", "")),
                            s.get("description", s.get("preview", ""))[:80]
                        )
                    self.console.print(table)
            elif subcmd in ("install", "add"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /skill install <path_to_skill>[/]")
                else:
                    src = parts[2]
                    res = install_skill(src)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] Skill '{res.get('name')}' installed successfully![/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
            elif subcmd in ("delete", "remove"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /skill delete <skill_name>[/]")
                else:
                    target = parts[2]
                    res = delete_skill(target)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] Skill '{target}' deleted.[/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
            else:
                self.console.print("[yellow]  Usage: /skill <list|install <path>|delete <name>>[/]")

        # ── /tool ────────────────────────────────────────────────────────────
        elif cmd == "/tool":
            from kurocode.tools.generator import tool_generator
            subcmd = parts[1].lower() if len(parts) > 1 else "list"
            if subcmd == "list":
                tools = tool_generator.list_generated_tools()
                if not tools:
                    self.console.print("[yellow]  No dynamic tools generated yet. Use /tool create <name> <code> to add one.[/]")
                else:
                    table = Table(title="Dynamically Generated Tools", border_style="cyan", box=box.ROUNDED)
                    table.add_column("Tool Name", style="bold cyan")
                    table.add_column("Description", style="white")
                    table.add_column("Path", style="dim")
                    for t in tools:
                        table.add_row(t.get("name", ""), t.get("description", ""), str(t.get("path", "")))
                    self.console.print(table)
            elif subcmd == "create":
                if len(parts) < 4:
                    self.console.print("[yellow]  Usage: /tool create <tool_name> <python_code>[/]")
                else:
                    tool_name = parts[2]
                    tool_code = " ".join(parts[3:])
                    res = tool_generator.generate_and_register(
                        name=tool_name,
                        code_body=tool_code,
                        description=f"Dynamic user tool {tool_name}",
                    )
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] Dynamic tool '{tool_name}' created, validated, and registered![/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
            else:
                self.console.print("[yellow]  Usage: /tool <list|create <name> <code>>[/]")

        # ── /heal ────────────────────────────────────────────────────────────
        elif cmd == "/heal":
            from kurocode.healing import healing_engine
            subcmd = parts[1].lower() if len(parts) > 1 else "status"
            if subcmd == "status":
                self.console.print(Panel(
                    f"[bold green]Status:[/] Active & Watching\n"
                    f"[bold yellow]Detector:[/] AST & Runtime Exception Classifier\n"
                    f"[bold yellow]Diagnostician:[/] Rule-based & LLM Diagnostic Pipeline\n"
                    f"[bold yellow]Repairer:[/] Pip resolver, Syntax autofixer, Directory recovery\n"
                    f"[bold yellow]Rollback:[/] Git checkpoint and snapshot manager enabled",
                    title="🩺 Dedicated Self-Healing Subsystem",
                    border_style="cyan",
                ))
            elif subcmd in ("repair", "fix"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /heal repair <tool_name> [error_message][/]")
                else:
                    tool_name = parts[2]
                    err_msg = " ".join(parts[3:]) if len(parts) > 3 else "Execution error"
                    self.console.print(f"[bold cyan]  Triggering diagnosis and repair for tool '{tool_name}'...[/]")
                    res = healing_engine.auto_heal(tool_name, err_msg)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] Repaired: {res.get('message')}[/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] Repair could not resolve automatically: {res.get('error')}[/]")
            else:
                self.console.print("[yellow]  Usage: /heal <status|repair <tool> [err]>[/]")

        # ── /evolve ──────────────────────────────────────────────────────────
        elif cmd == "/evolve":
            from kurocode.evolution import evolution_engine
            subcmd = parts[1].lower() if len(parts) > 1 else "propose"
            if subcmd == "propose":
                self.console.print("[bold cyan]  Running performance analysis and proposal engine...[/]")
                res = evolution_engine.run_evolution_cycle()
                if res.get("success"):
                    self.console.print(Panel(
                        f"[bold green]Proposal ID:[/] {res.get('proposal_id')}\n"
                        f"[bold yellow]Target Module:[/] {res.get('target_module')}\n"
                        f"[bold yellow]Action:[/] {res.get('action')}\n"
                        f"[bold white]Rationale:[/] {res.get('rationale')}\n"
                        f"[bold cyan]Status:[/] {res.get('status')}",
                        title="🧬 Controlled Self-Improvement Proposal",
                        border_style="cyan",
                    ))
                else:
                    self.console.print(f"[yellow]  {res.get('message', res.get('error', 'No evolution proposed.'))}[/]")
            elif subcmd in ("history", "log"):
                history = evolution_engine.ledger.get_history()
                if not history:
                    self.console.print("[yellow]  No evolution proposals in ledger.[/]")
                else:
                    table = Table(title="Evolution Proposal History", border_style="cyan", box=box.ROUNDED)
                    table.add_column("Proposal ID", style="bold cyan")
                    table.add_column("Target", style="yellow")
                    table.add_column("Action", style="green")
                    table.add_column("Status", style="magenta")
                    for p in history:
                        table.add_row(
                            p.get("proposal_id", ""),
                            p.get("target_module", ""),
                            p.get("action", ""),
                            p.get("status", "")
                        )
                    self.console.print(table)
            else:
                self.console.print("[yellow]  Usage: /evolve <propose|history>[/]")

        # ── /store (Puzzle Store & Hub) ───────────────────────────────────────
        elif cmd in ("/store", "/market", "/hub"):
            from kurocode.store import store_manager
            subcmd = parts[1].lower() if len(parts) > 1 else "list"

            if subcmd in ("list", "all"):
                filter_t = parts[2].lower() if len(parts) > 2 else None
                items = store_manager.list_kurohub(filter_t)
                table = Table(
                    title="🧩 Kuro Capability Store — Plug-and-Play Puzzle Pieces",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
                table.add_column("Type", justify="center", width=12)
                table.add_column("Piece Name", style="bold cyan")
                table.add_column("Status", justify="center", width=14)
                table.add_column("Author", style="dim", width=12)
                table.add_column("Description", style="white")

                type_colors = {
                    "tool": "[bold blue]TOOL[/]",
                    "plugin": "[bold magenta]PLUGIN[/]",
                    "skill": "[bold yellow]SKILL[/]",
                    "integration": "[bold green]INTEG[/]",
                }
                for it in items:
                    t_str = type_colors.get(it.item_type.value, it.item_type.value.upper())
                    status_str = "[bold green]✓ Installed[/]" if it.installed else "[dim]○ Available[/]"
                    table.add_row(t_str, it.name, status_str, it.author, it.description)
                self.console.print(table)
                self.console.print(
                    "[dim]  Install piece or URL: [cyan]/store install <name|url>[/cyan]  |  "
                    "Remove: [cyan]/store remove <name>[/cyan]  |  Sync Online Hub: [cyan]/store update[/cyan][/dim]\n"
                )

            elif subcmd in ("install", "add"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /store install <piece_name>[/]")
                else:
                    target_piece = parts[2]
                    self.console.print(f"[bold cyan]  Fetching and assembling puzzle piece '{target_piece}'...[/]")
                    res = store_manager.install(target_piece)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] {res.get('message')}[/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

            elif subcmd in ("remove", "uninstall", "delete"):
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /store remove <piece_name>[/]")
                else:
                    target_piece = parts[2]
                    res = store_manager.remove(target_piece)
                    if res.get("success"):
                        self.console.print(f"[bold green]  [OK] {res.get('message')}[/]")
                    else:
                        self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")

            elif subcmd == "search":
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /store search <query>[/]")
                else:
                    q = " ".join(parts[2:])
                    results = store_manager.search(q)
                    if not results:
                        self.console.print(f"[yellow]  No puzzle pieces matching '{q}' found in Store.[/]")
                    else:
                        table = Table(title=f"Store Search Results for '{q}'", border_style="cyan", box=box.ROUNDED)
                        table.add_column("Type", justify="center", width=12)
                        table.add_column("Piece Name", style="bold cyan")
                        table.add_column("Status", justify="center", width=14)
                        table.add_column("Description", style="white")
                        for it in results:
                            status_str = "[bold green]✓ Installed[/]" if it.installed else "[dim]○ Available[/]"
                            table.add_row(it.item_type.value.upper(), it.name, status_str, it.description)
                        self.console.print(table)

            elif subcmd == "info":
                if len(parts) < 3:
                    self.console.print("[yellow]  Usage: /store info <piece_name>[/]")
                else:
                    target_piece = parts[2]
                    it = store_manager.get_item(target_piece)
                    if not it:
                        self.console.print(f"[yellow]  Piece '{target_piece}' not found in store.[/]")
                    else:
                        payload_preview = json.dumps(it.payload, indent=2)
                        self.console.print(Panel(
                            f"[bold cyan]Name:[/] {it.name}\n"
                            f"[bold yellow]Type:[/] {it.item_type.value.upper()}\n"
                            f"[bold green]Status:[/] {'Installed' if it.installed else 'Available'}\n"
                            f"[bold white]Author:[/] {it.author}  (v{it.version})\n"
                            f"[bold magenta]Tags:[/] {', '.join(it.tags)}\n\n"
                            f"[bold white]Description:[/] {it.description}\n\n"
                            f"[bold cyan]Payload Blueprint:[/]\n{payload_preview[:1200]}",
                            title=f"🧩 Puzzle Piece: {it.name}",
                            border_style="cyan",
                        ))

            elif subcmd in ("update", "sync", "refresh"):
                remote_url = parts[2] if len(parts) > 2 else None
                self.console.print("[bold cyan]  🌐 Connecting to Online Community Hub (kuroLabs-ai/hub)...[/]")
                res = store_manager.update_from_remote(remote_url)
                if res.get("success"):
                    self.console.print(f"[bold green]  [OK] {res.get('message')}[/]")
                    if res.get("items"):
                        self.console.print(f"[dim]  Synced pieces: {', '.join(res.get('items', []))}[/dim]")
                else:
                    self.console.print(f"[bold red]  [FAIL] {res.get('error')}[/]")
                    if res.get("hint"):
                        self.console.print(Panel(
                            f"[yellow]{res.get('hint')}[/]\n\n"
                            f"[dim]KuroHub URL: {res.get('url')}[/dim]",
                            title="ℹ️ Hub Setup Info",
                            border_style="yellow",
                        ))

            else:
                self.console.print("[yellow]  Usage: /store <list|search <q>|install <name|url>|remove <name>|info <name>|update [url]>[/]")

        # ── dynamic skill execution: /<skill-name> [prompt] ────────────────────
        else:
            # Check if this matches an installed skill
            clean_cmd = cmd.lstrip("/")
            slug_candidates = [
                clean_cmd,
                clean_cmd.replace("-", "_"),
                clean_cmd.replace("_", "-"),
            ]
            
            matched_skill = None
            try:
                from kurocode.brain.kuro_hub import get_skills_kurohub
                skills_cat = get_skills_kurohub()
                for c in slug_candidates:
                    if c in skills_cat:
                        matched_skill = skills_cat[c]
                        break
            except Exception:
                pass

            if not matched_skill:
                try:
                    from kurocode.tools.self_improve import list_learned_skills
                    for s in list_learned_skills():
                        if s.get("slug") in slug_candidates or s.get("name") in slug_candidates:
                            matched_skill = s
                            break
                except Exception:
                    pass

            if matched_skill:
                # User invoked /<skill-name> [prompt]
                user_prompt = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
                skill_name = matched_skill.get("name", clean_cmd)
                skill_desc = matched_skill.get("description", "")
                skill_folder = matched_skill.get("folder", f"skills/{clean_cmd}")
                
                # Read skill README.md or skill.json
                skill_content = ""
                from kurocode.core.paths import SKILLS_DIR, USER_DATA_DIR
                possible_paths = [
                    SKILLS_DIR / clean_cmd.replace("-", "_") / "README.md",
                    SKILLS_DIR / clean_cmd.replace("-", "_") / "SKILL.md",
                    SKILLS_DIR / f"{clean_cmd.replace('-', '_')}.md",
                    USER_DATA_DIR / skill_folder / "README.md",
                ]
                for p in possible_paths:
                    if p.exists():
                        try:
                            skill_content = p.read_text(encoding="utf-8")
                            break
                        except Exception:
                            pass

                if not skill_content:
                    skill_content = f"# Skill: {skill_name}\n{skill_desc}"

                self.console.print(f"[bold cyan]  Executing skill:[/] [bold green]{skill_name}[/]")
                if user_prompt:
                    self.console.print(f"[dim]  User Prompt:[/] {user_prompt}")

                # Construct composite instruction for the LLM agent
                composed_prompt = (
                    f"Follow the procedural skill instructions below to accomplish the task.\n\n"
                    f"--- SKILL INSTRUCTIONS ({skill_name}) ---\n"
                    f"{skill_content}\n"
                    f"--- END SKILL INSTRUCTIONS ---\n\n"
                    f"TASK / USER PROMPT: {user_prompt if user_prompt else 'Execute this skill routine.'}"
                )
                # Return False so run_interactive dispatches composed_prompt to the agent!
                return False, composed_prompt

            self.console.print(f"[yellow]  Unknown command '{cmd}'. Type /help.[/]")

        return True, user_input

    # ─────────────────────────────────────────────────────────────────────────
    # run_interactive — full REPL loop
    # ─────────────────────────────────────────────────────────────────────────
    def run_interactive(self, agent: KuroAgent) -> None:
        """
        Starts the full interactive REPL.

        Sets up a CallbackHost wired to self._on_event and self._on_request,
        registers it with core.io_bus, then enters the prompt_toolkit REPL loop
        where every input is dispatched to slash commands, shell passthrough, or
        the autonomous agent.

        Ctrl+C mid-execution calls host.request_cancel().
        Ctrl+C / EOF at the idle prompt exits cleanly.
        """
        # Wire this adapter's callbacks into the io_bus for the session lifetime
        host = CallbackHost(on_event=self._on_event, on_request=self._on_request)
        _token = io_bus.set_host(host)

        # Render the full startup header
        self._print_header()

        # Build the prompt_toolkit session
        session: PromptSession = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=KuroCompleter(),
            style=PT_STYLE,
            key_bindings=self._kb,
            bottom_toolbar=self._get_bottom_toolbar,
            refresh_interval=1.0,
            enable_history_search=True,
            complete_while_typing=True,
            mouse_support=False,
            wrap_lines=True,
            lexer=SimpleLexer("class:"),
        )
        self._session = session

        try:
            while True:
                # Reset cancellation state before each new interaction
                host.reset_cancel()
                self._host = None  # No active agent run yet

                try:
                    provider_label = config.get_active_provider().upper()
                    prompt_tokens = HTML(
                        f'<ansibrightblack>[</ansibrightblack>'
                        f'<ansibrightcyan>KURO</ansibrightcyan>'
                        f'<ansibrightblack>|</ansibrightblack>'
                        f'<ansidarkgray>{provider_label}</ansidarkgray>'
                        f'<ansibrightblack>]</ansibrightblack> '
                        f'<ansiwhite>></ansiwhite> '
                    )

                    user_input = session.prompt(prompt_tokens).strip()

                except KeyboardInterrupt:
                    # Ctrl+C at the idle prompt — exit session
                    self.console.print()
                    self.console.print(
                        Rule("[bold cyan]KURO session ended.[/bold cyan]", style="cyan")
                    )
                    self.console.print()
                    break

                except EOFError:
                    self.console.print()
                    self.console.print(
                        Rule("[bold cyan]KURO session ended. Goodbye![/bold cyan]", style="cyan")
                    )
                    self.console.print()
                    break

                if not user_input:
                    continue

                # ── Exit keywords ─────────────────────────────────────────
                if user_input.lower() in ("exit", "quit", ":q", "bye"):
                    self.console.print()
                    self.console.print(
                        Rule("[bold cyan]KURO session ended. Goodbye![/bold cyan]", style="cyan")
                    )
                    self.console.print()
                    break

                # ── Slash command dispatch ────────────────────────────────
                if user_input.startswith("/"):
                    try:
                        should_continue, user_input = self._handle_slash_command(user_input, agent)
                        if should_continue:
                            continue
                        # If should_continue is False (e.g. /skill-name execution or /listen speech),
                        # fall through directly to autonomous agent dispatch below with the new user_input
                    except Exception as exc:
                        self.console.print(f"[bold red]  Command Error:[/] {exc}")
                        continue

                # ── Shell passthrough (! prefix) ──────────────────────────
                if user_input.startswith("!"):
                    shell_cmd = user_input[1:].strip()
                    if not shell_cmd:
                        self.console.print("[red]  No command given.[/]")
                        continue
                    res = run_command(shell_cmd, confirm_if_risky=config.SAFE_MODE)
                    self._print_shell_output(shell_cmd, res)
                    continue

                # ── Autonomous agent dispatch ─────────────────────────────
                self.console.print()
                self.console.print("[bold cyan]KURO is thinking...[/]")
                self._host = host  # expose host so Ctrl+C key binding can cancel

                try:
                    response = agent.run(user_input)
                except KeyboardInterrupt:
                    host.request_cancel()
                    self.console.print("\n[bold yellow]  ⚠ Run cancelled by user.[/]")
                    self._host = None
                    continue
                except Exception as exc:
                    self.console.print(f"[bold red]  Runtime Error:[/] {exc}")
                    self._host = None
                    continue

                self._host = None

                if response:
                    self.print_kuro_response(response)

        finally:
            # Restore the previous io_bus host
            io_bus.reset_host(_token)
            self._session = None
            self._host = None

    # ─────────────────────────────────────────────────────────────────────────
    # run_headless — single-shot non-interactive mode
    # ─────────────────────────────────────────────────────────────────────────
    def run_headless(self, agent: KuroAgent, query: str, json_output: bool = False) -> int:
        """
        Runs a single query non-interactively and prints the result.

        Args:
            agent:       Initialised KuroAgent.
            query:       The user query string (or a shell command starting with '!').
            json_output: If True, emits ``{"response": "...", "success": true}``
                         as JSON to stdout. Otherwise prints plain text.

        Returns:
            Exit code (0 = success, 1 = error).
        """
        # Use a NullHost — no interactive prompts in headless mode
        null_host = NullHost(auto_confirm=True)
        _token = io_bus.set_host(null_host)

        try:
            # Shell passthrough
            if query.startswith("!"):
                shell_cmd = query[1:].strip()
                res = run_command(shell_cmd)
                if json_output:
                    output = {
                        "response": res.get("stdout", "") + res.get("stderr", ""),
                        "success": res.get("returncode", 1) == 0,
                    }
                    print(json.dumps(output, ensure_ascii=False))
                else:
                    self._print_shell_output(shell_cmd, res)
                return 0 if res.get("returncode", 1) == 0 else 1

            # Slash command execution in headless mode
            if query.startswith("/"):
                if json_output:
                    # Capture status/pool in JSON format if requested
                    parts = query.split()
                    cmd = parts[0].lower()
                    if cmd == "/status":
                        s = {
                            "provider": config.get_active_provider(),
                            "model": config.get_active_model(),
                            "safe_mode": config.SAFE_MODE,
                            "git_checkpoints": config.AUTO_GIT_CHECKPOINTS,
                        }
                        print(json.dumps({"response": s, "success": True}, ensure_ascii=False))
                        return 0
                    elif cmd == "/pool":
                        pool = config.get_pool_status_summary()
                        print(json.dumps({"response": pool, "success": True}, ensure_ascii=False))
                        return 0

                self._handle_slash_command(query, agent)
                return 0

            # Agent query
            if not json_output:
                self.console.print("[cyan]KURO is thinking...[/]")


            response = agent.run(query)

            if json_output:
                output = {"response": response or "", "success": True}
                print(json.dumps(output, ensure_ascii=False))
            else:
                self.print_kuro_response(response or "")

            return 0

        except Exception as exc:
            if json_output:
                print(json.dumps({"response": str(exc), "success": False}, ensure_ascii=False))
            else:
                self.console.print(f"[bold red]  Error:[/] {exc}")
            return 1

        finally:
            io_bus.reset_host(_token)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience: a singleton CLIAdapter for use from main.py
# ─────────────────────────────────────────────────────────────────────────────
_adapter: CLIAdapter | None = None


def get_adapter() -> CLIAdapter:
    """Returns the module-level singleton CLIAdapter (creates it if needed)."""
    global _adapter
    if _adapter is None:
        _adapter = CLIAdapter()
    return _adapter

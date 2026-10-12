# KURO 2.0 (`kurocode`) Architecture Overview

> **Version:** 2.0 (package `kurocode` v0.2.0)  
> **Package Root:** `src/kurocode`  
> **Core Architecture:** Level 2 ReAct Autonomous Agent with Deterministic Verification & Self-Healing

---

## 1. High-Level Topology

KURO 2.0 is built on an event-driven, decoupled pipeline separating presentation, orchestration, domain capabilities, and persistent storage:

```
┌────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                   │
│   • CLIAdapter (Rich Console + prompt_toolkit REPL)    │
│   • Headless Runner (--query / --json)                 │
│   • 30+ Slash Commands & Shell Bypass (!<cmd>)         │
└──────────────────────────┬─────────────────────────────┘
                           │ CoreEvent / InputRequest
                           ▼
┌────────────────────────────────────────────────────────┐
│                   I/O BUS (`io_bus`)                   │
│   • Decoupled IOHost & CallbackHost protocol           │
│   • Graceful cancellation (Ctrl+C request_cancel)      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                 CORE RE-ACT AGENT LOOP                 │
│                                                        │
│   1. Task Registry (`task_state.py`): PENDING ➔ RUN    │
│   2. Model Router (`model_router.py`): Query routing   │
│   3. Context Engine (`context_engine.py`): Token cap   │
│   4. LLM Dispatch (`llm.py`): Multi-Key rotation       │
│   5. Safe Action Parser: Triple-backtick & regex JSON  │
│   6. Permission Gate (`permissions.py`): Risk checks   │
│   7. Tool Execution (`tools/`, `PluginRegistry`)       │
│   8. Verification Engine (`verification.py`)           │
│   9. Self-Healing Engine (`healing/`) on errors        │
│  10. Memory & Evolution Commit (`memory_db`, `ledger`) │
└────────────────────────────────────────────────────────┘
```

---

## 2. Directory Layout & Subsystem Responsibilities

| Subsystem Path | Primary Purpose | Key Modules |
| :--- | :--- | :--- |
| **`src/kurocode/cli/`** | Application bootstrap and launch modes | [`app.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/cli/app.py) |
| **`src/kurocode/adapters/`** | Presentation layer (Terminal REPL, prompt styles, slash dispatch) | [`cli.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/adapters/cli.py) |
| **`src/kurocode/core/`** | Core agent loop, model routing, safety gates, context budgeting, SQLite database, DPAPI vault | [`agent.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/agent.py), [`model_router.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/model_router.py), [`permissions.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/permissions.py), [`context_engine.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/context_engine.py), [`memory_db.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/memory_db.py), [`vault.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/vault.py), [`sandbox.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/core/sandbox.py) |
| **`src/kurocode/tools/`** | Built-in capabilities (Filesystem, Shell, Python, Web, Browser, Vision, Git, Notifier) | [`files.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/tools/files.py), [`system.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/tools/system.py), [`interpreter.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/tools/interpreter.py), [`web_browser.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/tools/web_browser.py), [`vision.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/tools/vision.py), [`notifier.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/tools/notifier.py) |
| **`src/kurocode/healing/`** | Autonomous self-healing subsystem | [`detector.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/healing/detector.py), [`diagnostician.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/healing/diagnostician.py), [`repairer.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/healing/repairer.py), [`rollback.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/healing/rollback.py) |
| **`src/kurocode/evolution/`** | Controlled self-improvement and capability synthesis | [`analyzer.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/evolution/analyzer.py), [`improver.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/evolution/improver.py), [`generator.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/evolution/generator.py), [`tester.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/evolution/tester.py), [`versioning.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/evolution/versioning.py) |
| **`src/kurocode/store/`** | Modular capability marketplace and catalog | [`manager.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/store/manager.py), [`catalog.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/store/catalog.py) |
| **`src/kurocode/plugins/`** | External plugin discovery, validation, and lifecycle | [`manager.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/plugins/manager.py), [`loader.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/plugins/loader.py), [`validator.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/plugins/validator.py) |
| **`src/kurocode/integrations/`** | Connected external service adapters (Telegram, Discord, GitHub, Drive, GitLab) | [`base.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/integrations/base.py), [`telegram_integration.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/integrations/telegram_integration.py), [`discord_integration.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/integrations/discord_integration.py), [`github_integration.py`](file:///d:/vscode/Kuro.worktrees/kurocode/src/kurocode/integrations/github_integration.py) |

---

## 3. Fundamental Invariants

1. **Deterministic Verification**: No tool action is deemed complete simply because it did not raise an unhandled exception. The `VerificationEngine` independently verifies file existence, sizes, valid Python AST syntax via `py_compile`, and process return codes.
2. **Safety by Default**: In `SAFE_MODE=true`, all mutating, external, or destructive actions halt execution and prompt for user confirmation.
3. **Encrypted Credentials**: Secrets are encrypted using Windows DPAPI (`CryptProtectData`) or PBKDF2/AES-256; no plain-text credentials are ever stored or exposed in logs.
4. **Resilient Provider Cascade**: API rate limits (HTTP 429) automatically put the specific key in cooldown for 60 seconds and rotate through key pools and fallback providers seamlessly.

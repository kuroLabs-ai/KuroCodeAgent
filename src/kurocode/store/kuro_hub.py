"""
src/kurocode/store/kuro_hub.py — Built-in KuroHub of puzzle-piece capabilities.
Curated, tested, and plug-and-play Tools, Plugins, Skills, and Integrations.
"""

from __future__ import annotations

import copy
from .models import StoreItem, StoreItemType

# ─────────────────────────────────────────────────────────────────────────────
# Embedded Source Code Payloads for Builtin Tools
# ─────────────────────────────────────────────────────────────────────────────

_JSON_INSPECTOR_CODE = '''def json_inspector(text: str, indent: int = 2) -> dict:
    """Format, validate and inspect JSON text."""
    import json
    try:
        data = json.loads(text)
        return {
            "success": True,
            "valid": True,
            "formatted": json.dumps(data, indent=indent),
            "type": type(data).__name__,
            "keys": list(data.keys()) if isinstance(data, dict) else len(data),
        }
    except Exception as e:
        return {"success": False, "valid": False, "error": str(e)}
'''

_HASH_CALCULATOR_CODE = '''def hash_calculator(text: str, algorithm: str = "sha256") -> dict:
    """Calculate cryptographic hash (md5, sha1, sha256, sha512)."""
    import hashlib
    algo = algorithm.lower().strip()
    if not hasattr(hashlib, algo):
        return {"success": False, "error": f"Unsupported hash algorithm: {algo}"}
    digest = getattr(hashlib, algo)(text.encode("utf-8")).hexdigest()
    return {"success": True, "algorithm": algo, "digest": digest}
'''

_BASE64_CODEC_CODE = '''def base64_codec(text: str, mode: str = "encode") -> dict:
    """Base64 encode or decode text."""
    import base64
    try:
        if mode.lower() == "encode":
            res = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        else:
            res = base64.b64decode(text.encode("utf-8")).decode("utf-8")
        return {"success": True, "result": res, "mode": mode}
    except Exception as e:
        return {"success": False, "error": str(e)}
'''

_HTTP_PINGER_CODE = '''def http_pinger(url: str, timeout: int = 5) -> dict:
    """Pings an HTTP/HTTPS URL and measures status and latency."""
    import urllib.request, time
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Kuro-Pinger/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = round((time.time() - start) * 1000, 2)
            return {"success": True, "status": resp.status, "latency_ms": latency, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": round((time.time() - start) * 1000, 2)}
'''

# ─────────────────────────────────────────────────────────────────────────────
# Embedded Source Code Payloads for Builtin Plugins
# ─────────────────────────────────────────────────────────────────────────────

_CODE_METRICS_CODE = '''import ast
from pathlib import Path

def analyze_file(path_str: str) -> dict:
    p = Path(path_str)
    if not p.exists():
        return {"success": False, "error": "File not found"}
    content = p.read_text(encoding="utf-8")
    lines = content.splitlines()
    try:
        tree = ast.parse(content)
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        return {"success": True, "lines": len(lines), "functions": len(funcs), "classes": len(classes)}
    except Exception as e:
        return {"success": False, "error": f"Parse error: {e}"}

def register(registry):
    registry.register_function("code_metrics", "Analyze lines and functions in code", analyze_file)
'''

_CHANGELOG_GENERATOR_CODE = '''import subprocess

def generate_changelog(max_commits: int = 15) -> dict:
    try:
        cmd = ["git", "log", f"-n{max_commits}", "--pretty=format:- %s (%h)"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            md = "# Changelog\\n\\n### Recent Changes\\n" + "\\n".join(lines)
            return {"success": True, "changelog": md, "commit_count": len(lines)}
        return {"success": False, "error": res.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def register(registry):
    registry.register_function("generate_changelog", "Generate markdown changelog from git", generate_changelog)
'''

# ─────────────────────────────────────────────────────────────────────────────
# Embedded Markdown Payloads for Builtin Skills
# ─────────────────────────────────────────────────────────────────────────────

_TDD_REFACTORING_MD = """# TDD Refactoring Skill Routine

Follow these disciplined steps when refactoring:
1. **Baseline**: Run `pytest` before making edits.
2. **Specification**: Add test covering expected behavior.
3. **Minimal Edit**: Implement fix without bloat.
4. **Clean Code**: Refactor and format cleanly.
5. **Regression Verification**: Confirm all tests pass.
"""

_SECURITY_AUDIT_MD = """# Security Audit Routine

Execute whenever integrating new modules or external code:
1. Scan AST for banned system calls (`ctypes`, `subprocess` misuse).
2. Mask credentials into Encrypted Vault.
3. Confirm risk classification (SAFE, CONFIRM, DANGEROUS).
"""

_DOCKER_PIPELINE_MD = """# Docker Pipeline Routine

Procedure for containerized workflows:
1. Build image: `docker build -t app:latest .`
2. Run container: `docker run --rm -d -p 8080:8080 app:latest`
3. Verify and teardown.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Built-in Catalog Entries (Tools, Plugins, Skills, Integrations)
# ─────────────────────────────────────────────────────────────────────────────

BUILTIN_PUZZLE_PIECES: list[StoreItem] = [
    # ── TOOLS (Single .py files) ─────────────────────────────────────────────
    StoreItem(
        id="tool_json_inspector",
        name="json_inspector",
        item_type=StoreItemType.TOOL,
        description="Fast JSON formatter, syntax validator, and schema inspector.",
        author="Kuro Team",
        tags=["json", "formatting", "parser", "utility"],
        file_path="tools/json_inspector.py",
        payload={
            "code": _JSON_INSPECTOR_CODE,
            "entrypoint": "json_inspector",
        },
    ),
    StoreItem(
        id="tool_hash_calculator",
        name="hash_calculator",
        item_type=StoreItemType.TOOL,
        description="Compute MD5, SHA1, SHA256, or SHA512 cryptographic checksums.",
        author="Kuro Team",
        tags=["crypto", "hash", "security", "checksum"],
        file_path="tools/hash_calculator.py",
        payload={
            "code": _HASH_CALCULATOR_CODE,
            "entrypoint": "hash_calculator",
        },
    ),
    StoreItem(
        id="tool_base64_codec",
        name="base64_codec",
        item_type=StoreItemType.TOOL,
        description="Encode or decode Base64 strings with UTF-8 character support.",
        author="Kuro Team",
        tags=["encoding", "base64", "codec", "utility"],
        file_path="tools/base64_codec.py",
        payload={
            "code": _BASE64_CODEC_CODE,
            "entrypoint": "base64_codec",
        },
    ),
    StoreItem(
        id="tool_http_pinger",
        name="http_pinger",
        item_type=StoreItemType.TOOL,
        description="Pings an HTTP/HTTPS endpoint and measures latency and HTTP status code.",
        author="Kuro Team",
        tags=["network", "ping", "http", "diagnostics"],
        file_path="tools/http_pinger.py",
        payload={
            "code": _HTTP_PINGER_CODE,
            "entrypoint": "http_pinger",
        },
    ),

    # ── PLUGINS (Full Folders) ───────────────────────────────────────────────
    StoreItem(
        id="plugin_code_metrics",
        name="code_metrics",
        item_type=StoreItemType.PLUGIN,
        description="Analyzes Python source files to calculate lines of code, docstring ratio, and function count.",
        author="Kuro Team",
        tags=["analytics", "ast", "metrics", "quality"],
        dir_path="plugins/code_metrics",
        payload={
            "manifest": {
                "name": "code_metrics",
                "version": "1.0.0",
                "description": "Code complexity and size analyzer plugin",
                "entrypoint": "main.py",
                "author": "Kuro Team",
            },
            "code": _CODE_METRICS_CODE,
        },
    ),
    StoreItem(
        id="plugin_changelog_generator",
        name="changelog_generator",
        item_type=StoreItemType.PLUGIN,
        description="Generates KeepAChangelog-formatted markdown entries from recent git commit history.",
        author="Kuro Team",
        tags=["git", "changelog", "release", "docs"],
        dir_path="plugins/changelog_generator",
        payload={
            "manifest": {
                "name": "changelog_generator",
                "version": "1.0.0",
                "description": "KeepAChangelog markdown generator",
                "entrypoint": "main.py",
                "author": "Kuro Team",
            },
            "code": _CHANGELOG_GENERATOR_CODE,
        },
    ),

    # ── SKILLS (Full Folders) ────────────────────────────────────────────────
    StoreItem(
        id="skill_tdd_refactoring",
        name="tdd_refactoring",
        item_type=StoreItemType.SKILL,
        description="Test-Driven Development refactoring routine (Red -> Green -> Refactor -> Verify).",
        author="Kuro Team",
        tags=["methodology", "tdd", "refactoring", "testing"],
        dir_path="skills/tdd_refactoring",
        payload={
            "name": "tdd_refactoring",
            "description": "Standardized procedure for TDD refactoring cycles",
            "steps": [
                "1. Run existing test suite to establish green baseline.",
                "2. Write targeted failing unit test for new behavior or uncovered bug.",
                "3. Make minimal implementation change to achieve green test status.",
                "4. Refactor code for readability, type safety, and PEP standards.",
                "5. Re-run complete test suite to ensure zero regressions.",
            ],
            "markdown": _TDD_REFACTORING_MD,
        },
    ),
    StoreItem(
        id="skill_security_audit",
        name="security_audit",
        item_type=StoreItemType.SKILL,
        description="Automated security inspection routine checking AST dangerous calls, secrets, and permissions.",
        author="Kuro Team",
        tags=["security", "audit", "ast", "compliance"],
        dir_path="skills/security_audit",
        payload={
            "name": "security_audit",
            "description": "Routine for full code and environment security auditing",
            "steps": [
                "1. Run sandbox AST scan on modified Python source files.",
                "2. Inspect .env and configuration files for unmasked raw secrets.",
                "3. Verify permission policies in core/permissions.py for new tools.",
                "4. Validate file paths against path traversal escaping checks.",
                "5. Generate structured audit summary report.",
            ],
            "markdown": _SECURITY_AUDIT_MD,
        },
    ),
    StoreItem(
        id="skill_docker_pipeline",
        name="docker_pipeline",
        item_type=StoreItemType.SKILL,
        description="Procedure for building, testing, and containerizing application services with Docker.",
        author="Kuro Team",
        tags=["devops", "docker", "containers", "deployment"],
        dir_path="skills/docker_pipeline",
        payload={
            "name": "docker_pipeline",
            "description": "Docker container build and test pipeline routine",
            "steps": [
                "1. Verify Dockerfile exists and contains valid multi-stage builds.",
                "2. Run docker build with tag and build-args.",
                "3. Launch container with health check probe.",
                "4. Run integration tests against exposed container endpoints.",
                "5. Clean up temporary containers and dangling images.",
            ],
            "markdown": _DOCKER_PIPELINE_MD,
        },
    ),

    # ── INTEGRATIONS (Full Folders) ──────────────────────────────────────────
    StoreItem(
        id="integration_gitlab",
        name="gitlab",
        item_type=StoreItemType.INTEGRATION,
        description="GitLab REST API connector for repository inspection, issue tracking, and CI/CD pipelines.",
        author="Kuro Team",
        tags=["vcs", "gitlab", "git", "ci-cd"],
        dir_path="integrations/gitlab",
        payload={
            "service": "gitlab",
            "default_host": "https://gitlab.com",
            "actions": ["list_projects", "list_issues", "pipeline_status"],
        },
    ),
    StoreItem(
        id="integration_slack",
        name="slack",
        item_type=StoreItemType.INTEGRATION,
        description="Slack Webhook connector for dispatching operational alerts and team notifications.",
        author="Kuro Team",
        tags=["messaging", "slack", "alerts", "chat"],
        dir_path="integrations/slack",
        payload={
            "service": "slack",
            "default_url": "https://hooks.slack.com/services/...",
            "actions": ["send_message", "send_alert"],
        },
    ),
]


def get_default_kurohub() -> list[StoreItem]:
    """Returns a fresh copy of the default store items."""
    return copy.deepcopy(BUILTIN_PUZZLE_PIECES)


__all__ = ["BUILTIN_PUZZLE_PIECES", "get_default_kurohub"]

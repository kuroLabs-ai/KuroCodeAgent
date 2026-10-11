"""
src/kurocode/store/catalog.py — Built-in Catalog of puzzle-piece capabilities.
Curated, tested, and plug-and-play Tools, Plugins, Skills, and Integrations.
"""

from __future__ import annotations

from typing import Dict, List
from .models import StoreItem, StoreItemType


BUILTIN_PUZZLE_PIECES: List[StoreItem] = [
    # ── TOOLS ────────────────────────────────────────────────────────────────
    StoreItem(
        id="tool_json_inspector",
        name="json_inspector",
        item_type=StoreItemType.TOOL,
        description="Fast JSON formatter, syntax validator, and schema inspector.",
        author="Kuro Team",
        tags=["json", "formatting", "parser", "utility"],
        payload={
            "code": (
                "def json_inspector(text: str, indent: int = 2) -> dict:\n"
                "    '''Format, validate and inspect JSON text.'''\n"
                "    import json\n"
                "    try:\n"
                "        data = json.loads(text)\n"
                "        return {\n"
                "            'success': True,\n"
                "            'valid': True,\n"
                "            'formatted': json.dumps(data, indent=indent),\n"
                "            'type': type(data).__name__,\n"
                "            'keys': list(data.keys()) if isinstance(data, dict) else len(data),\n"
                "        }\n"
                "    except Exception as e:\n"
                "        return {'success': False, 'valid': False, 'error': str(e)}\n"
            ),
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
        payload={
            "code": (
                "def hash_calculator(text: str, algorithm: str = 'sha256') -> dict:\n"
                "    '''Calculate cryptographic hash (md5, sha1, sha256, sha512).'''\n"
                "    import hashlib\n"
                "    algo = algorithm.lower().strip()\n"
                "    if not hasattr(hashlib, algo):\n"
                "        return {'success': False, 'error': f'Unsupported hash algorithm: {algo}'}\n"
                "    digest = getattr(hashlib, algo)(text.encode('utf-8')).hexdigest()\n"
                "    return {'success': True, 'algorithm': algo, 'digest': digest}\n"
            ),
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
        payload={
            "code": (
                "def base64_codec(text: str, mode: str = 'encode') -> dict:\n"
                "    '''Base64 encode or decode text.'''\n"
                "    import base64\n"
                "    try:\n"
                "        if mode.lower() == 'encode':\n"
                "            res = base64.b64encode(text.encode('utf-8')).decode('utf-8')\n"
                "        else:\n"
                "            res = base64.b64decode(text.encode('utf-8')).decode('utf-8')\n"
                "        return {'success': True, 'result': res, 'mode': mode}\n"
                "    except Exception as e:\n"
                "        return {'success': False, 'error': str(e)}\n"
            ),
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
        payload={
            "code": (
                "def http_pinger(url: str, timeout: int = 5) -> dict:\n"
                "    '''Pings an HTTP/HTTPS URL and measures status and latency.'''\n"
                "    import urllib.request, time\n"
                "    start = time.time()\n"
                "    try:\n"
                "        req = urllib.request.Request(url, headers={'User-Agent': 'Kuro-Pinger/1.0'})\n"
                "        with urllib.request.urlopen(req, timeout=timeout) as resp:\n"
                "            latency = round((time.time() - start) * 1000, 2)\n"
                "            return {'success': True, 'status': resp.status, 'latency_ms': latency, 'url': url}\n"
                "    except Exception as e:\n"
                "        return {'success': False, 'error': str(e), 'latency_ms': round((time.time() - start) * 1000, 2)}\n"
            ),
            "entrypoint": "http_pinger",
        },
    ),

    # ── PLUGINS ──────────────────────────────────────────────────────────────
    StoreItem(
        id="plugin_code_metrics",
        name="code_metrics",
        item_type=StoreItemType.PLUGIN,
        description="Analyzes Python source files to calculate lines of code, docstring ratio, and function count.",
        author="Kuro Team",
        tags=["analytics", "ast", "metrics", "quality"],
        payload={
            "manifest": {
                "name": "code_metrics",
                "version": "1.0.0",
                "description": "Code complexity and size analyzer plugin",
                "entrypoint": "main.py",
                "author": "Kuro Hub",
            },
            "code": (
                "import ast\n"
                "from pathlib import Path\n"
                "\n"
                "def analyze_file(path_str: str) -> dict:\n"
                "    p = Path(path_str)\n"
                "    if not p.exists():\n"
                "        return {'success': False, 'error': 'File not found'}\n"
                "    content = p.read_text(encoding='utf-8')\n"
                "    lines = content.splitlines()\n"
                "    try:\n"
                "        tree = ast.parse(content)\n"
                "        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]\n"
                "        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]\n"
                "        return {'success': True, 'lines': len(lines), 'functions': len(funcs), 'classes': len(classes)}\n"
                "    except Exception as e:\n"
                "        return {'success': False, 'error': f'Parse error: {e}'}\n"
                "\n"
                "def register(registry):\n"
                "    registry.register_function('code_metrics', 'Analyze lines and functions in code', analyze_file)\n"
            ),
        },
    ),
    StoreItem(
        id="plugin_changelog_generator",
        name="changelog_generator",
        item_type=StoreItemType.PLUGIN,
        description="Generates KeepAChangelog-formatted markdown entries from recent git commit history.",
        author="Kuro Team",
        tags=["git", "changelog", "release", "docs"],
        payload={
            "manifest": {
                "name": "changelog_generator",
                "version": "1.0.0",
                "description": "KeepAChangelog markdown generator",
                "entrypoint": "main.py",
                "author": "Kuro Hub",
            },
            "code": (
                "import subprocess\n"
                "\n"
                "def generate_changelog(max_commits: int = 15) -> dict:\n"
                "    try:\n"
                "        cmd = ['git', 'log', f'-n{max_commits}', '--pretty=format:- %s (%h)']\n"
                "        res = subprocess.run(cmd, capture_output=True, text=True)\n"
                "        if res.returncode == 0:\n"
                "            lines = res.stdout.strip().splitlines()\n"
                "            md = '# Changelog\\n\\n### Recent Changes\\n' + '\\n'.join(lines)\n"
                "            return {'success': True, 'changelog': md, 'commit_count': len(lines)}\n"
                "        return {'success': False, 'error': res.stderr}\n"
                "    except Exception as e:\n"
                "        return {'success': False, 'error': str(e)}\n"
                "\n"
                "def register(registry):\n"
                "    registry.register_function('generate_changelog', 'Generate markdown changelog from git', generate_changelog)\n"
            ),
        },
    ),

    # ── SKILLS ───────────────────────────────────────────────────────────────
    StoreItem(
        id="skill_tdd_refactoring",
        name="tdd_refactoring",
        item_type=StoreItemType.SKILL,
        description="Test-Driven Development refactoring routine (Red -> Green -> Refactor -> Verify).",
        author="Kuro Team",
        tags=["methodology", "tdd", "refactoring", "testing"],
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
            "markdown": (
                "# TDD Refactoring Skill Routine\n\n"
                "Follow these disciplined steps when refactoring:\n"
                "1. **Baseline**: Run `pytest` before making edits.\n"
                "2. **Specification**: Add test covering expected behavior.\n"
                "3. **Minimal Edit**: Implement fix without bloat.\n"
                "4. **Clean Code**: Refactor and format cleanly.\n"
                "5. **Regression Verification**: Confirm all tests pass.\n"
            ),
        },
    ),
    StoreItem(
        id="skill_security_audit",
        name="security_audit",
        item_type=StoreItemType.SKILL,
        description="Automated security inspection routine checking AST dangerous calls, secrets, and permissions.",
        author="Kuro Team",
        tags=["security", "audit", "ast", "compliance"],
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
            "markdown": (
                "# Security Audit Routine\n\n"
                "Execute whenever integrating new modules or external code:\n"
                "1. Scan AST for banned system calls (`ctypes`, `subprocess` misuse).\n"
                "2. Mask credentials into Encrypted Vault.\n"
                "3. Confirm risk classification (SAFE, CONFIRM, DANGEROUS).\n"
            ),
        },
    ),
    StoreItem(
        id="skill_docker_pipeline",
        name="docker_pipeline",
        item_type=StoreItemType.SKILL,
        description="Procedure for building, testing, and containerizing application services with Docker.",
        author="Kuro Team",
        tags=["devops", "docker", "containers", "deployment"],
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
            "markdown": (
                "# Docker Pipeline Routine\n\n"
                "Procedure for containerized workflows:\n"
                "1. Build image: `docker build -t app:latest .`\n"
                "2. Run container: `docker run --rm -d -p 8080:8080 app:latest`\n"
                "3. Verify and teardown.\n"
            ),
        },
    ),

    # ── INTEGRATIONS ─────────────────────────────────────────────────────────
    StoreItem(
        id="integration_gitlab",
        name="gitlab",
        item_type=StoreItemType.INTEGRATION,
        description="GitLab REST API connector for repository inspection, issue tracking, and CI/CD pipelines.",
        author="Kuro Team",
        tags=["vcs", "gitlab", "git", "ci-cd"],
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
        payload={
            "service": "slack",
            "default_url": "https://hooks.slack.com/services/...",
            "actions": ["send_message", "send_alert"],
        },
    ),
]


def get_default_catalog() -> List[StoreItem]:
    """Returns a fresh copy of the default store items."""
    import copy
    return copy.deepcopy(BUILTIN_PUZZLE_PIECES)


__all__ = ["BUILTIN_PUZZLE_PIECES", "get_default_catalog"]

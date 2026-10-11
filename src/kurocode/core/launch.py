"""
core/launch.py — Argument parsing and execution-mode selection.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass
class LaunchArgs:
    mode: str  # cli | headless
    query: str = ""
    json_output: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    gui: bool = False
    cli: bool = False
    raw: Optional[argparse.Namespace] = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kuro",
        description="KURO 2.0 — Autonomous CLI Agent & Terminal Workspace.",
        add_help=True,
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Optional request or slash command. Runs headless CLI and exits.",
    )
    parser.add_argument("--cli", "--console", dest="cli", action="store_true",
                        help="Force interactive terminal / REPL mode.")
    parser.add_argument("--json", dest="json_output", action="store_true",
                        help="Emit structured JSON (headless / automation).")
    parser.add_argument("--provider", "-p", default=None, help="Override LLM provider.")
    parser.add_argument("--model", "-m", default=None, help="Override LLM model.")
    return parser


def parse_launch_args(argv: Optional[Sequence[str]] = None) -> LaunchArgs:
    parser = build_parser()
    ns = parser.parse_args(argv)
    query = " ".join(ns.query).strip()

    if query:
        mode = "headless"
    else:
        mode = "cli"

    return LaunchArgs(
        mode=mode,
        query=query,
        json_output=bool(ns.json_output),
        provider=ns.provider,
        model=ns.model,
        gui=False,
        cli=bool(ns.cli),
        raw=ns,
    )


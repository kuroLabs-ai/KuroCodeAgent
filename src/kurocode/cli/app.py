"""CLI bootstrap for the KuroCode package entry point."""

from __future__ import annotations

import os
import sys
from typing import List, Optional

# Suppress pygame startup banner before any import triggers it
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ.setdefault("UNICODE_VERSION", "15.1.0")

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from kurocode.core.launch import parse_launch_args
from kurocode.core.agent import KuroAgent
from kurocode.adapters.cli import CLIAdapter


def run(argv: Optional[List[str]] = None) -> None:
    """Run KuroCode CLI application."""
    if argv is None:
        argv = sys.argv[1:]

    args = parse_launch_args(argv)

    if args.provider:
        os.environ["KURO_PROVIDER"] = args.provider.lower()

    if args.mode == "headless":
        agent = KuroAgent()
        if args.model:
            agent.model = args.model
        cli = CLIAdapter()
        cli.run_headless(agent, args.query, json_output=args.json_output)
        sys.exit(0)
    else:
        agent = KuroAgent()
        if args.model:
            agent.model = args.model
        cli = CLIAdapter()
        cli.run_interactive(agent)


def main() -> None:
    run()


if __name__ == "__main__":
    run()

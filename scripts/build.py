"""Build helper for KuroCode packaging."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the KuroCode package")
    parser.add_argument("--output", default="dist")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Build target prepared at: {out.resolve()}")


if __name__ == "__main__":
    main()

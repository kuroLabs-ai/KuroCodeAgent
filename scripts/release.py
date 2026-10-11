"""Release packaging helper."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a release build")
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    print(f"Release version {args.version} is ready for packaging.")


if __name__ == "__main__":
    main()

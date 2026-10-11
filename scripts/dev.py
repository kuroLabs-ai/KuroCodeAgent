"""Development helper for local KuroCode runs."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "-m", "kurocode"], check=False)


if __name__ == "__main__":
    main()

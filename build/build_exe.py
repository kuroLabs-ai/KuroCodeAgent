"""Build KURO as a console application."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List


BUILD_MODES = ("console",)
APP_NAMES = {"console": "KuroConsole"}


def build_command(mode: str, base_dir: Path) -> List[str]:
    """Return the PyInstaller command for the console application."""
    if mode != "console":
        raise ValueError(f"Unsupported build mode: {mode}")

    name = APP_NAMES["console"]
    icon = base_dir / "assets" / "kuro_icon.ico"
    if not icon.is_file():
        icon = base_dir / "assets" / "kuro_icon.png"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--contents-directory=.",
        f"--name={name}",
        f"--icon={icon}",
        f"--distpath={base_dir / 'dist'}",
        f"--workpath={base_dir / 'build' / 'pyinstaller' / name}",
        f"--specpath={base_dir / 'build'}",
        "--console",
        f"--runtime-hook={base_dir / 'build' / 'runtime_hooks' / 'kuro_console.py'}",
    ]

    data_separator = os.pathsep
    for directory in (
        "core",
        "constants",
        "tools",
        "integrations",
        "adapters",
        "brain",
        "assets",
        "config",
        "skills",
    ):
        source = base_dir / directory
        if source.is_dir():
            command.extend(["--add-data", f"{source}{data_separator}{directory}"])

    command.extend([
        "--collect-all=kurocode",
        "--collect-all=rich",
        "--collect-all=prompt_toolkit",
        "--hidden-import=ctypes",
        "--hidden-import=cryptography",
        "--hidden-import=edge_tts",
        "--hidden-import=pygame",
        "--hidden-import=speech_recognition",
    ])

    command.append(str(base_dir / "main.py"))
    return command


def build_standalone_exe(mode: str = "console", dry_run: bool = False) -> bool:
    """Build standalone console app distribution."""
    if mode not in BUILD_MODES:
        raise ValueError(f"Unsupported build mode: {mode}")

    if not dry_run:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print(
                "[Error] PyInstaller is not installed. Install project dependencies "
                "with: python -m pip install -r requirements.txt"
            )
            return False

    base_dir = Path(__file__).resolve().parent.parent
    command = build_command(mode, base_dir)
    print(f"\n[Build] {mode.upper()} executable")
    print("[Build] " + subprocess.list2cmdline(command))
    if not dry_run:
        result = subprocess.run(command, cwd=str(base_dir), check=False)
        if result.returncode != 0:
            print(f"[Error] {mode} build failed (exit code {result.returncode}).")
            return False

        name = APP_NAMES[mode]
        executable = base_dir / "dist" / name / f"{name}.exe"
        if not executable.is_file():
            print(f"[Error] PyInstaller succeeded but expected executable is missing: {executable}")
            return False
        print(f"[Success] {executable}")

    if dry_run:
        print("\n[Dry run] No files were built.")
    else:
        print("\n[Success] Requested KURO executable build completed.")
    return True


def combined_build_command(base_dir: Path) -> List[str]:
    """Return the PyInstaller command for the shared KuroCode distribution."""
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        f"--distpath={base_dir / 'dist'}",
        f"--workpath={base_dir / 'build' / 'pyinstaller' / 'KuroCode'}",
        str(base_dir / "build" / "KuroCode.spec"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=BUILD_MODES,
        default="console",
        help="Build the console app (default: console).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the PyInstaller commands without building.",
    )
    args = parser.parse_args()
    return 0 if build_standalone_exe(args.mode, dry_run=args.dry_run) else 1


if __name__ == "__main__":
    raise SystemExit(main())


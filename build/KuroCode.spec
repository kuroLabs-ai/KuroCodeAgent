# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


base_dir = Path(SPECPATH).parent
datas = []
binaries = []
hiddenimports = [
    "ctypes",
    "cryptography",
    "edge_tts",
    "pygame",
    "speech_recognition",
]

for package in ("rich", "prompt_toolkit"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

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
        datas.append((str(source), directory))

icon = base_dir / "assets" / "kuro_icon.ico"
if not icon.is_file():
    icon = base_dir / "assets" / "kuro_icon.png"

analysis = Analysis(
    [str(base_dir / "main.py")],
    pathex=[str(base_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(base_dir / "build" / "runtime_hooks" / "kuro_shared.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

console_exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="KuroConsole",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon),
    contents_directory=".",
)

distribution = COLLECT(
    console_exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KuroCode",
)


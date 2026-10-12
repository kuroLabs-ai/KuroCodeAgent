# KURO 2.0 Local Development & Testing Guide

> **Target Python Versions:** 3.10, 3.11, 3.12, 3.13  
> **Recommended OS:** Windows 10/11, Linux, or macOS

---

## 1. Environment Initialization

```bash
# 1. Clone the repository
git clone https://github.com/Abdo-omran2206/KuroAgent.git
cd KuroAgent

# 2. Create virtual environment
python -m venv .venv

# 3. Activate environment
# On Windows (cmd/PowerShell):
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

# 4. Install build dependencies and requirements
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 5. Install kurocode in editable development mode
pip install -e .
```

---

## 2. Running & Testing KURO

### Interactive CLI Mode
```bash
# Launch interactive REPL
kuro
# or
python main.py
```

### Headless Single-Shot Mode
```bash
# Run single prompt
kuro "Analyze codebase structure and report dependencies"

# Run single prompt with JSON output
kuro --json "Inspect active git branch"
```

---

## 3. Test Suite Execution

KURO has an extensive pytest suite covering advanced agent capabilities, evolution, self-awareness, and marketplace functionality:

```bash
# Run all tests
pytest -v

# Run targeted test suites
pytest tests/test_advanced_capabilities.py
pytest tests/test_evolution.py
pytest tests/test_store_marketplace.py
pytest tests/test_self_awareness.py
pytest tests/test_dual_interface.py
```

---

## 4. Standalone Executable & Distribution Build

KURO includes automated PyInstaller and Inno Setup packaging scripts:

```bash
# Build standalone console application (dist/KuroConsole/KuroConsole.exe)
python build/build_exe.py

# Package Windows Installer via Inno Setup (requires ISCC in PATH)
build\build_installer.bat
```

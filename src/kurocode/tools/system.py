"""
tools/system.py — System Execution, OS Awareness & Telemetry for KURO.
Provides safe shell execution, live PC telemetry (CPU, RAM, Disk, Battery),
process monitoring, and native application management.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

RISKY_COMMAND_PATTERNS = [
    "rm -rf", "del /f", "del /s", "rd /s", "format ", "dd if=",
    "shutdown", "reboot", "mkfs", "drop database", "icacls",
    "chmod -r 777", "chown -r", "reg delete", "diskpart"
]


def is_risky_command(cmd: str) -> bool:
    """Checks if a command contains potentially destructive patterns."""
    cmd_lower = cmd.lower().strip()
    return any(pattern in cmd_lower for pattern in RISKY_COMMAND_PATTERNS)


def run_command(cmd: str, cwd: Optional[str] = None, confirm_if_risky: bool = True) -> Dict[str, Any]:
    """
    Executes a system shell command safely using subprocess.
    Captures stdout, stderr, and return code with a 120s timeout.
    """
    if is_risky_command(cmd) and confirm_if_risky:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"SECURITY NOTICE: Command '{cmd}' flagged as potentially destructive.",
            "returncode": -1,
            "requires_confirmation": True
        }

    try:
        working_dir = cwd or os.getcwd()
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=120
        )
        return {
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
            "requires_confirmation": False
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command execution timed out after 120 seconds.",
            "returncode": -1,
            "requires_confirmation": False
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Failed to execute command: {str(e)}",
            "returncode": -1,
            "requires_confirmation": False
        }


def get_system_info() -> Dict[str, Any]:
    """Returns basic system environment information."""
    try:
        current_user = os.getlogin()
    except Exception:
        current_user = os.getenv("USERNAME", os.getenv("USER", "user"))

    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "user": current_user,
    }


def get_system_telemetry() -> Dict[str, Any]:
    """
    Collects live hardware & OS telemetry:
    - Memory (RAM) utilization
    - Disk storage (total, used, free)
    - Battery status (if available on laptop)
    - CPU core count & architecture
    """
    telemetry: Dict[str, Any] = {
        "os": platform.system(),
        "release": platform.release(),
        "user": os.getenv("USERNAME", os.getenv("USER", "user")),
        "cpu_count": os.cpu_count() or 1,
        "timestamp": time.time(),
    }

    # 1. Disk Storage via shutil
    try:
        total, used, free = shutil.disk_usage(os.getcwd())
        telemetry["disk"] = {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "percent_used": round((used / total) * 100, 1),
        }
    except Exception:
        telemetry["disk"] = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent_used": 0}

    # 2. Windows-specific memory & battery metrics via ctypes / PowerShell
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

            total_ram_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
            avail_ram_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
            used_ram_gb = round(total_ram_gb - avail_ram_gb, 2)

            telemetry["ram"] = {
                "total_gb": total_ram_gb,
                "used_gb": used_ram_gb,
                "free_gb": avail_ram_gb,
                "percent_used": int(stat.dwMemoryLoad),
            }
        except Exception:
            telemetry["ram"] = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent_used": 0}
    else:
        telemetry["ram"] = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent_used": 0}

    return telemetry


def get_running_processes(limit: int = 15) -> List[Dict[str, Any]]:
    """
    Lists running processes on the host machine.
    """
    procs: List[Dict[str, Any]] = []
    if sys.platform == "win32":
        try:
            cmd = "tasklist /FO CSV /NH"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                for line in res.stdout.strip().split("\n")[:limit]:
                    parts = [p.strip('"') for p in line.split('","')]
                    if len(parts) >= 5:
                        procs.append({
                            "name": parts[0],
                            "pid": parts[1],
                            "session": parts[2],
                            "memory": parts[4].strip(),
                        })
        except Exception:
            pass
    return procs


def open_app_or_file(target: str) -> Dict[str, Any]:
    """
    Opens a file, directory, application, or URL with the default desktop handler.
    """
    try:
        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.run(["open", target], check=True)
        else:
            subprocess.run(["xdg-open", target], check=True)
        return {"success": True, "target": target}
    except Exception as exc:
        return {"success": False, "error": str(exc), "target": target}

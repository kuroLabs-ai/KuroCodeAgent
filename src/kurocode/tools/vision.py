"""
tools/vision.py — Vision analysis and screen capture for KURO.
"""

from __future__ import annotations

import base64
import datetime
import mimetypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def get_image_bytes_and_mime(image_path: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Validates and reads an image file, returning (raw_bytes, mime_type, error_msg).
    """
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        return None, None, f"Image file not found: {image_path}"
    if not path.is_file():
        return None, None, f"Path is not a file: {image_path}"

    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type or not mime_type.startswith("image/"):
        ext = path.suffix.lower()
        if ext in (".png", ".apng"):
            mime_type = "image/png"
        elif ext in (".jpg", ".jpeg"):
            mime_type = "image/jpeg"
        elif ext in (".webp",):
            mime_type = "image/webp"
        elif ext in (".gif",):
            mime_type = "image/gif"
        else:
            return None, None, f"Unsupported image format '{ext}'. Supported: png, jpg, jpeg, webp, gif."

    try:
        raw_bytes = path.read_bytes()
        return raw_bytes, mime_type, None
    except Exception as e:
        return None, None, f"Failed to read image file: {str(e)}"


def analyze_image_tool(
    image_path: str,
    prompt: str = "Describe this image in detail and highlight key information."
) -> Dict[str, Any]:
    """
    Tool function used by KURO agent to inspect local images.
    """
    raw_bytes, mime_type, err = get_image_bytes_and_mime(image_path)
    if err:
        return {"success": False, "error": err}

    b64_data = base64.b64encode(raw_bytes).decode("utf-8")
    return {
        "success": True,
        "image_path": str(image_path),
        "mime_type": mime_type,
        "b64_data": b64_data,
        "prompt": prompt,
        "size_kb": round(len(raw_bytes) / 1024, 2)
    }


def capture_screen(save_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Captures the primary monitor screenshot and saves it locally.
    Returns {"success": True, "path": path} or {"success": False, "error": msg}.
    """
    out_dir = Path("cache") / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    if save_path:
        target = Path(save_path).resolve()
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target = (out_dir / f"screen_{timestamp}.png").resolve()

    # Strategy 1: PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(str(target), "PNG")
        return {"success": True, "path": str(target), "method": "PIL"}
    except Exception:
        pass

    # Strategy 2: Windows PowerShell Drawing fallback
    if sys.platform == "win32":
        try:
            ps_script = (
                f"Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
                f"$b = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); "
                f"$g = [System.Drawing.Graphics]::FromImage($b); "
                f"$g.CopyFromScreen(0,0,0,0,$b.Size); "
                f"$b.Save('{str(target).replace(chr(92), '/')}'); "
                f"$b.Dispose(); $g.Dispose();"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=10)
            if target.exists() and target.stat().st_size > 0:
                return {"success": True, "path": str(target), "method": "PowerShell"}
        except Exception as exc:
            return {"success": False, "error": f"Screen capture failed: {str(exc)}"}

    return {"success": False, "error": "No screen capture backend available in this environment."}

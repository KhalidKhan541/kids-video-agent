"""Blender tools: verify setup, render scenes, and compose output."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from src.config import settings


def find_blender() -> Optional[Path]:
    """Find Blender executable on the system."""
    blender_path = settings.BLENDER_EXECUTABLE
    if blender_path and Path(blender_path).exists():
        return Path(blender_path)

    candidates = [
        Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender 4.1/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender 4.0/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender 3.6/blender.exe"),
        Path("C:/Program Files/Blender Foundation/Blender/blender.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c

    import shutil
    which = shutil.which("blender")
    if which:
        return Path(which)

    return None


def verify_blender() -> dict:
    """Check if Blender is available and return version info."""
    blender = find_blender()
    if not blender:
        return {"available": False, "version": "", "path": "", "error": "Not found"}

    try:
        result = subprocess.run(
            [str(blender), "--version"],
            capture_output=True, text=True, timeout=30,
        )
        first_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        return {
            "available": True,
            "version": first_line.strip(),
            "path": str(blender),
            "error": "",
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return {"available": False, "version": "", "path": str(blender), "error": str(e)}


def render_script(script_path: Path, output_path: Optional[Path] = None,
                  timeout: int = 600) -> dict:
    """Execute a Blender Python script in background mode."""
    blender = find_blender()
    if not blender:
        return {"success": False, "error": "Blender not found", "path": ""}

    cmd = [str(blender), "--background", "--python", str(script_path)]

    if output_path:
        cmd.extend(["--", "--output", str(output_path)])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
            "error": result.stderr[:200] if result.returncode != 0 else "",
            "path": str(output_path) if output_path else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout after {timeout}s", "path": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "path": ""}


def render_scene_blend(scene_script: str, output_path: Path,
                        duration_seconds: int = 15, fps: int = 24) -> dict:
    """Generate a .blend file from a Python script and render frames."""
    blender = find_blender()
    if not blender:
        return {"success": False, "error": "Blender not found"}

    blend_path = output_path.with_suffix(".blend")
    script_path = output_path.parent / f"{output_path.stem}_script.py"

    script_path.write_text(scene_script, encoding="utf-8")

    # First pass: generate the .blend file (don't render)
    try:
        subprocess.run(
            [str(blender), "--background", "--python", str(script_path)],
            capture_output=True, text=True, timeout=300,
        )
    except Exception as e:
        return {"success": False, "error": f"Blend generation failed: {e}"}

    # Second pass: render the .blend
    render_path = output_path.with_suffix(".mp4")
    try:
        result = subprocess.run(
            [str(blender), "--background", str(blend_path), "--render-anim",
             "--engine", "CYCLES" if False else "EEVEE",
             "--render-output", str(render_path.with_suffix("")),
             "--frame-end", str(duration_seconds * fps)],
            capture_output=True, text=True, timeout=600,
        )
        return {
            "success": result.returncode == 0,
            "output": str(render_path),
            "error": result.stderr[:300] if result.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Render timeout (600s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}

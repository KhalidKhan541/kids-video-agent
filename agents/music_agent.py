"""MusicAgent - Searches and downloads free stock music from Pixabay."""

from pathlib import Path
from typing import Any


def run(topic: str, output_dir: Path, **kwargs) -> dict[str, Any]:
    try:
        from src.tools.music_tools import get_kids_bgm
        music_path = get_kids_bgm(output_dir=output_dir)
        if music_path:
            return {"agent": "MusicAgent", "path": str(music_path), "success": True}
        return {"agent": "MusicAgent", "success": False, "error": "No music found"}
    except Exception as e:
        return {"agent": "MusicAgent", "error": str(e), "success": False}

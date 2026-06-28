"""VoiceNarrator Agent - Generates voiceovers using Piper TTS (local, free)."""

from pathlib import Path
from typing import Any


def run(scenes: list[dict], output_dir: Path, lang: str = "en", **kwargs) -> dict[str, Any]:
    try:
        from src.tools.piper_tts_tools import generate_narration_segments
        segments = [{"text": s.get("narration", s.get("narration_text", "")), "filename": f"scene_{s['scene_id']:03d}.wav"} for s in scenes]
        audio_files = generate_narration_segments(segments, output_dir=str(output_dir))
        return {"agent": "VoiceNarrator", "count": len(audio_files), "files": audio_files, "success": True}
    except Exception as e:
        return {"agent": "VoiceNarrator", "error": str(e), "success": False}

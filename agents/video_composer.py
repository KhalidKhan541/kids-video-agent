"""VideoComposer Agent - Assembles video from images + audio using FFmpeg."""

from pathlib import Path
from typing import Any


def run(image_paths: list, audio_paths: list, output_path: Path, bgm_path: Path | None = None, **kwargs) -> dict[str, Any]:
    try:
        from src.tools.ffmpeg_tools import compose_video

        images_dir = output_path.parent / "images"
        audio_dir = output_path.parent / "audio"

        if image_paths and not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
            for i, img in enumerate(image_paths):
                import shutil
                dst = images_dir / f"scene_{i+1:03d}.png"
                if Path(img).exists():
                    shutil.copy2(img, dst)

        if audio_paths and not audio_dir.exists():
            audio_dir.mkdir(parents=True, exist_ok=True)
            for i, aud in enumerate(audio_paths):
                import shutil
                dst = audio_dir / f"narration_{i+1:03d}.wav"
                if Path(aud).exists():
                    shutil.copy2(aud, dst)

        result = compose_video(
            images_dir=images_dir,
            audio_dir=audio_dir,
            output_path=output_path,
            bgm_path=bgm_path,
        )
        result["agent"] = "VideoComposer"
        return result
    except Exception as e:
        return {"agent": "VideoComposer", "error": str(e), "success": False}

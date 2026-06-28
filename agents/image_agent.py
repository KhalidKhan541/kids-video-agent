"""ImageGenerator Agent - Generates images using Pollinations.ai (free)."""

from pathlib import Path
from typing import Any


def run(scenes: list[dict], output_dir: Path, **kwargs) -> dict[str, Any]:
    try:
        from src.tools.image_tools import generate_batch
        prompts = [s.get("image_prompt", s.get("description", "")) for s in scenes]
        image_paths = generate_batch(prompts, output_dir=str(output_dir))
        return {"agent": "ImageGenerator", "success_count": len(image_paths), "total": len(prompts), "paths": image_paths}
    except Exception as e:
        return {"agent": "ImageGenerator", "error": str(e), "success_count": 0}

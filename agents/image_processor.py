"""Agent 3: ImageProcessor - Resizes, crops, formats images for video."""

from pathlib import Path
from typing import Any

from PIL import Image


WIDTH = 1280
HEIGHT = 720


def run(images_dir: Path, output_dir: Path, width: int = WIDTH, height: int = HEIGHT, **kwargs) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = Path(images_dir)

    exts = {".png", ".jpg", ".jpeg", ".webp"}
    images = sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in exts and p.is_file()
    )

    if not images:
        return {
            "agent": "ImageProcessor",
            "success": False,
            "error": f"No images found in {images_dir}",
            "processed": [],
        }

    processed = []
    for img_path in images:
        out_path = output_dir / f"{img_path.stem}_processed.png"
        try:
            _resize_and_crop(img_path, out_path, width, height)
            processed.append({
                "input": str(img_path),
                "output": str(out_path),
                "width": width,
                "height": height,
                "success": True,
            })
        except Exception as e:
            processed.append({
                "input": str(img_path),
                "error": str(e),
                "success": False,
            })

    return {
        "agent": "ImageProcessor",
        "input_dir": str(images_dir),
        "output_dir": str(output_dir),
        "processed": processed,
        "total": len(images),
        "success_count": sum(1 for p in processed if p["success"]),
        "fail_count": sum(1 for p in processed if not p["success"]),
        "success": True,
    }


def _resize_and_crop(img_path: Path, output_path: Path, width: int, height: int):
    img = Image.open(img_path).convert("RGB")
    orig_w, orig_h = img.size
    target_ratio = width / height
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        new_h = height
        new_w = int(height * orig_ratio)
    else:
        new_w = width
        new_h = int(width / orig_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    img = img.crop((left, top, left + width, top + height))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", optimize=True)

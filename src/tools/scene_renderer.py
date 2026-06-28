"""Fast scene renderer using Pillow + MoviePy. No Blender required."""

import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.config import settings


COLOR_PALETTES = [
    [(135, 206, 250), (255, 215, 0)],
    [(144, 238, 144), (255, 165, 0)],
    [(221, 160, 221), (255, 255, 150)],
    [(255, 127, 80), (100, 149, 237)],
    [(150, 200, 255), (255, 200, 100)],
]


def render_scene_image(
    scene: dict,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    scene_index: int = 0,
) -> Path:
    """Render a scene as a colorful image (fast)."""
    palette = COLOR_PALETTES[scene_index % len(COLOR_PALETTES)]

    # Fast gradient using numpy
    c1, c2 = palette
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for ch in range(3):
        arr[:, :, ch] = np.linspace(c1[ch], c2[ch], height, dtype=np.uint8).reshape(-1, 1)

    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    # Fast decorations — fewer shapes
    rng = random.Random(scene_index * 42 + 7)
    for _ in range(8):
        x, y = rng.randint(0, width), rng.randint(0, height)
        sz = rng.randint(10, 30)
        draw.ellipse([x - sz, y - sz, x + sz, y + sz], fill=(255, 255, 200))

    for _ in range(4):
        x, y = rng.randint(50, width - 50), rng.randint(50, height - 50)
        sz = rng.randint(15, 35)
        color = rng.choice([(255, 182, 193), (144, 238, 144), (173, 216, 230)])
        draw.rectangle([x - sz, y - sz, x + sz, y + sz], fill=color, outline="white", width=2)

    # Narration text
    narration = scene.get("narration", "")
    if narration:
        _draw_text(draw, narration, width, height)

    # Scene badge
    _draw_badge(draw, scene.get("scene_id", scene_index + 1))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", optimize=True)
    return output_path


def render_scene_to_clip(
    scene: dict,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    scene_index: int = 0,
    duration: int = 5,
    fps: int = 12,
) -> Path:
    """Render scene image and convert to video clip (fast, uses ffmpeg)."""
    img_path = output_path.with_suffix(".png")
    render_scene_image(scene, img_path, width, height, scene_index)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg directly — much faster than MoviePy for static images
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
             "-c:v", "libx264", "-t", str(duration),
             "-pix_fmt", "yuv420p", "-vf", f"scale={width}:{height}",
             "-r", str(fps), "-preset", "ultrafast",
             str(output_path)],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and output_path.exists():
            try:
                img_path.unlink()
            except Exception:
                pass
            return output_path
    except Exception:
        pass

    # Fallback: MoviePy
    try:
        from moviepy import ImageClip
        clip = ImageClip(str(img_path), duration=duration).with_fps(fps)
        clip.write_videofile(str(output_path), codec="libx264",
                             preset="ultrafast", logger=None)
        clip.close()
        try:
            img_path.unlink()
        except Exception:
            pass
        return output_path
    except Exception:
        pass

    return output_path


def render_all_scenes(
    scenes: list[dict],
    output_dir: Path,
    width: int = 1280,
    height: int = 720,
    duration: int = 5,
    fps: int = 12,
) -> list[Path]:
    """Render all scenes to video clips."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = []

    for i, scene in enumerate(scenes):
        clip_path = output_dir / f"scene_{i+1:03d}.mp4"
        render_scene_to_clip(scene, clip_path, width, height, i, duration, fps)
        if clip_path.exists():
            clips.append(clip_path)

    return clips


def _draw_text(draw: ImageDraw, text: str, w: int, h: int):
    """Draw centered text with shadow."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) * 20 < w - 100:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)

    font_size = 40
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    y_start = (h - len(lines) * 55) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        y = y_start + i * 55
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)


def _draw_badge(draw: ImageDraw, scene_id: int):
    """Draw scene number badge."""
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.rounded_rectangle([15, 15, 120, 45], radius=8, fill=(0, 0, 0))
    draw.text((25, 18), f"Scene {scene_id}", fill=(255, 255, 255), font=font)

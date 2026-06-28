from PIL import Image, ImageDraw, ImageFont
import math
from pathlib import Path
from src.config import settings
from src.agent.state import AgentState


class ThumbnailCreatorNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        topic = proj.get("topic", "kids video")
        lang = proj.get("language", "en")

        output_path = settings.THUMBNAILS_DIR / f"{topic.replace(' ', '_').lower()}.jpg"
        self._generate_thumbnail(topic, output_path, lang)

        meta = proj.get("youtube_metadata", {})
        meta["thumbnail_path"] = str(output_path)

        return {
            "project": {
                **proj,
                "thumbnail_path": str(output_path),
                "youtube_metadata": meta,
                "status": "thumbnail_created",
            },
            "logs": [f"[Thumbnail] Created: {output_path.name}"],
        }

    def _generate_thumbnail(self, title: str, path: Path, lang: str):
        w, h = 1280, 720
        img = self._create_gradient_bg(w, h)
        draw = ImageDraw.Draw(img)

        self._draw_stars(draw, w, h)
        self._draw_rainbow(draw, w, h)
        self._draw_text(draw, title, w, h)

        img.save(path, quality=95)

    def _create_gradient_bg(self, w: int, h: int) -> Image.Image:
        try:
            import numpy as np
            arr = np.zeros((h, w, 3), dtype=np.uint8)
            for y in range(h):
                t = y / h
                arr[y, :] = [
                    int(255 * (1 - t) + 100 * t),
                    int(100 * (1 - t) + 200 * t),
                    int(200 * (1 - t) + 255 * t),
                ]
            return Image.fromarray(arr)
        except ImportError:
            return Image.new("RGB", (w, h), (173, 216, 230))

    def _draw_stars(self, draw: ImageDraw, w: int, h: int):
        import random
        rng = random.Random(42)
        for _ in range(30):
            x = rng.randint(0, w)
            y = rng.randint(0, h // 2)
            size = rng.randint(3, 8)
            color = (255, 255, rng.randint(150, 255))
            draw.regular_polygon((x, y, size), n_sides=4, rotation=rng.randint(0, 90), fill=color, outline=color)

    def _draw_rainbow(self, draw: ImageDraw, w: int, h: int):
        rainbow = [(255, 0, 0), (255, 127, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (75, 0, 130), (139, 0, 255)]
        for i, color in enumerate(rainbow):
            y_offset = h - 80 + i * 8
            draw.arc([100, y_offset, w - 100, y_offset + 120], start=0, end=180, fill=color, width=6)

    def _draw_text(self, draw: ImageDraw, title: str, w: int, h: int):
        from PIL import ImageFont
        font_size = 48
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        lines = []
        words = title.split()
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bb = draw.textbbox((0, 0), test, font=font)
            if bb[2] - bb[0] < w - 200:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)

        y_start = h // 2 - len(lines) * 30
        for i, line in enumerate(lines):
            bb = draw.textbbox((0, 0), line, font=font)
            x = (w - (bb[2] - bb[0])) // 2
            y = y_start + i * 55

            draw.text((x + 2, y + 2), line, fill="black", font=font)
            draw.text((x, y), line, fill="white", font=font)

        sub_text = "Fun Kids Video"
        try:
            small_font = ImageFont.truetype("arial.ttf", 28)
        except (OSError, IOError):
            small_font = ImageFont.load_default()
        bb2 = draw.textbbox((0, 0), sub_text, font=small_font)
        sx = (w - (bb2[2] - bb2[0])) // 2
        draw.text((sx, h - 150), sub_text, fill="white", font=small_font)

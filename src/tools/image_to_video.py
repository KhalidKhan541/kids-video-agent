"""Convert AI-generated images into animated video clips with narration.

Core pipeline: reads images, applies Ken Burns effect, adds gTTS narration,
mixes background music, and assembles a final MP4 video.
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut

from src.tools.tts_tools import (
    add_background_music,
    combine_audio_segments,
    generate_narration,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 24
SCENE_DURATION_DEFAULT = 8
FADE_DURATION = 0.8  # seconds of cross-fade between scenes
SCENE_GAP_MS = 600  # silence between narration segments (ms)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}

KEN_BURNS_EFFECTS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_font(size: int = 48) -> ImageFont.FreeTypeFont:
    """Locate a usable TrueType font on the system."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize *img* so it fully covers *target_w* x *target_h* (centre-crop).

    Preserves aspect ratio — no stretching.
    """
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _collect_images(folder: Path) -> list[Path]:
    """Return sorted list of image files in *folder*."""
    files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda p: p.name)
    return files


# ---------------------------------------------------------------------------
# Ken Burns helper — builds a zoom/pan function for moviepy's `make_frame`
# ---------------------------------------------------------------------------

def _ken_burns_make_frame(
    img_array,
    effect: str,
    duration: float,
):
    """Return a *make_frame(t)* closure that applies the Ken Burns effect.

    Parameters
    ----------
    img_array : numpy.ndarray
        Source image as HxWx3 array (already cropped to target size).
    effect : str
        One of zoom_in, zoom_out, pan_left, pan_right, pan_up.
    duration : float
        Clip duration in seconds.
    """
    import numpy as np

    src_h, src_w = img_array.shape[:2]
    out_w, out_h = WIDTH, HEIGHT

    # We scale the source up to 1.3x so we have room to pan/zoom
    scale = 1.3
    big_w = int(src_w * scale)
    big_h = int(src_h * scale)
    big = np.array(
        Image.fromarray(img_array).resize((big_w, big_h), Image.Resampling.LANCZOS)
    )

    def make_frame(t):
        progress = t / max(duration, 1e-6)  # 0 → 1

        if effect == "zoom_in":
            # Start at 100% crop of the big image, end at 70% (zoom in)
            frac = 1.0 - 0.35 * progress
            crop_w = int(out_w * frac * scale / 1.0)
            crop_h = int(out_h * frac * scale / 1.0)
            crop_w = min(crop_w, big_w)
            crop_h = min(crop_h, big_h)
            x = (big_w - crop_w) // 2
            y = (big_h - crop_h) // 2
            frame = big[y : y + crop_h, x : x + crop_w]
            frame_img = Image.fromarray(frame).resize((out_w, out_h), Image.Resampling.LANCZOS)
            return np.array(frame_img)

        if effect == "zoom_out":
            frac = 0.65 + 0.35 * progress
            crop_w = int(out_w * frac * scale / 1.0)
            crop_h = int(out_h * frac * scale / 1.0)
            crop_w = min(crop_w, big_w)
            crop_h = min(crop_h, big_h)
            x = (big_w - crop_w) // 2
            y = (big_h - crop_h) // 2
            frame = big[y : y + crop_h, x : x + crop_w]
            frame_img = Image.fromarray(frame).resize((out_w, out_h), Image.Resampling.LANCZOS)
            return np.array(frame_img)

        if effect == "pan_left":
            max_pan = big_w - out_w
            x = int(max_pan * (1.0 - progress))
            y = (big_h - out_h) // 2
            frame = big[y : y + out_h, x : x + out_w]
            return frame

        if effect == "pan_right":
            max_pan = big_w - out_w
            x = int(max_pan * progress)
            y = (big_h - out_h) // 2
            frame = big[y : y + out_h, x : x + out_w]
            return frame

        if effect == "pan_up":
            max_pan = big_h - out_h
            x = (big_w - out_w) // 2
            y = int(max_pan * (1.0 - progress))
            frame = big[y : y + out_h, x : x + out_w]
            return frame

        # Fallback — static centre crop
        x = (big_w - out_w) // 2
        y = (big_h - out_h) // 2
        return big[y : y + out_h, x : x + out_w]

    return make_frame


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class ImageToVideoPipeline:
    """Convert a folder of images into an animated video with narration.

    Parameters
    ----------
    input_dir : Path
        Directory containing source images.
    output_dir : Path
        Where to write temp audio files and the final video.
    """

    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir = self.output_dir / "_temp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def create_video(
        self,
        topic: str,
        narration_scripts: list[dict] | None = None,
    ) -> Path:
        """Create a full video from images in *input_dir*.

        Parameters
        ----------
        topic : str
            Video topic — used for the title screen and auto-narration.
        narration_scripts : list[dict], optional
            Each dict may contain:
            - scene_number (int)
            - narration (str)
            - image_filename (str)
            - duration (int, default 8)
            If *None*, scenes are built from discovered images.

        Returns
        -------
        Path
            Path to the final MP4 file.
        """
        images = _collect_images(self.input_dir)
        if not images:
            raise FileNotFoundError(f"No images found in {self.input_dir}")

        scenes = self._build_scene_list(images, narration_scripts, topic)

        print(f"[ImageToVideo] Processing {len(scenes)} scenes …")

        # 1. Generate narration audio per scene
        narration_paths = self._generate_all_narrations(scenes)

        # 2. Combine narration into single track
        combined_narration = self._temp_dir / "combined_narration.wav"
        combine_audio_segments(narration_paths, combined_narration, gap_ms=SCENE_GAP_MS)

        # 3. Mix with background music
        final_audio = self._temp_dir / "final_audio.wav"
        add_background_music(combined_narration, final_audio, music_volume=0.4)

        # 4. Build video clips
        video_clips = []
        for scene in scenes:
            clip = self._build_scene_clip(scene)
            video_clips.append(clip)

        # 5. Prepend title + append ending
        title_clip = self._create_title_clip(topic, duration=5)
        ending_clip = self._create_ending_clip(topic, duration=4)
        all_clips = [title_clip] + video_clips + [ending_clip]

        # 6. Assemble
        output_path = self.output_dir / f"{topic.replace(' ', '_').lower()}.mp4"
        self._assemble_final(all_clips, final_audio, output_path)

        print(f"[ImageToVideo] Done -> {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Ken Burns
    # ------------------------------------------------------------------

    def _apply_ken_burns(self, image_path: Path, duration: int, effect: str = "zoom_in"):
        """Apply Ken Burns effect to a single image, returning a moviepy clip.

        Parameters
        ----------
        image_path : Path
            Source image.
        duration : int
            Clip duration in seconds.
        effect : str
            zoom_in | zoom_out | pan_left | pan_right | pan_up
        """
        import numpy as np

        img = Image.open(image_path).convert("RGB")
        img = _fit_image(img, WIDTH, HEIGHT)
        img_array = np.array(img)

        make_frame = _ken_burns_make_frame(img_array, effect, duration)

        from moviepy import VideoClip
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(FPS)
        return clip

    # ------------------------------------------------------------------
    # Title / ending screens
    # ------------------------------------------------------------------

    def _create_title_clip(self, topic: str, duration: int = 5):
        """Create an animated title screen with a coloured background."""
        import numpy as np

        bg_color = (30, 30, 80)  # dark blue

        def make_frame(t):
            progress = t / max(duration, 1e-6)
            # Gentle fade-in from black
            alpha = min(1.0, progress * 3)
            frame = np.full((HEIGHT, WIDTH, 3), bg_color, dtype=np.uint8)
            frame = (frame * alpha).astype(np.uint8)

            # Build PIL overlay for text
            overlay = Image.fromarray(frame)
            draw = ImageDraw.Draw(overlay)
            font_title = _find_font(64)
            font_sub = _find_font(32)

            title_text = topic.upper()
            bbox = draw.textbbox((0, 0), title_text, font=font_title)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                ((WIDTH - tw) // 2, (HEIGHT - th) // 2 - 30),
                title_text,
                fill=(255, 220, 100),
                font=font_title,
            )

            sub_text = "A Fun Learning Adventure"
            bbox2 = draw.textbbox((0, 0), sub_text, font=font_sub)
            sw = bbox2[2] - bbox2[0]
            draw.text(
                ((WIDTH - sw) // 2, (HEIGHT // 2) + 50),
                sub_text,
                fill=(200, 200, 200),
                font=font_sub,
            )
            return np.array(overlay)

        from moviepy import VideoClip
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(FPS)
        clip = clip.with_effects([FadeIn(FADE_DURATION), FadeOut(FADE_DURATION)])
        return clip

    def _create_ending_clip(self, topic: str, duration: int = 3):
        """Create an ending screen with a subscribe call-to-action."""
        import numpy as np

        bg_color = (20, 60, 20)  # dark green

        def make_frame(t):
            progress = t / max(duration, 1e-6)
            alpha = 1.0 - progress * 0.3
            frame = np.full((HEIGHT, WIDTH, 3), bg_color, dtype=np.uint8)
            frame = (frame * alpha).astype(np.uint8)

            overlay = Image.fromarray(frame)
            draw = ImageDraw.Draw(overlay)
            font_main = _find_font(52)
            font_sub = _find_font(28)

            text1 = "Thanks for Watching!"
            bbox1 = draw.textbbox((0, 0), text1, font=font_main)
            w1 = bbox1[2] - bbox1[0]
            draw.text(
                ((WIDTH - w1) // 2, (HEIGHT // 2) - 60),
                text1,
                fill=(255, 255, 255),
                font=font_main,
            )

            text2 = "Subscribe for more fun videos!"
            bbox2 = draw.textbbox((0, 0), text2, font=font_sub)
            w2 = bbox2[2] - bbox2[0]
            draw.text(
                ((WIDTH - w2) // 2, (HEIGHT // 2) + 30),
                text2,
                fill=(200, 200, 200),
                font=font_sub,
            )
            return np.array(overlay)

        from moviepy import VideoClip
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(FPS)
        clip = clip.with_effects([FadeIn(FADE_DURATION), FadeOut(FADE_DURATION)])
        return clip

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_scene_list(
        self,
        images: list[Path],
        narration_scripts: list[dict] | None,
        topic: str,
    ) -> list[dict]:
        """Normalise scene descriptions into a uniform list."""
        if narration_scripts:
            scenes = []
            for entry in narration_scripts:
                img_name = entry.get("image_filename", "")
                img_path = self.input_dir / img_name
                if not img_path.exists():
                    # fuzzy match: find image whose stem contains the name
                    for im in images:
                        if img_name and img_name.lower() in im.stem.lower():
                            img_path = im
                            break
                if not img_path.exists():
                    idx = entry.get("scene_number", len(scenes) + 1) - 1
                    img_path = images[min(idx, len(images) - 1)]
                scenes.append({
                    "image_path": img_path,
                    "narration": entry.get("narration", ""),
                    "duration": entry.get("duration", SCENE_DURATION_DEFAULT),
                    "effect": random.choice(KEN_BURNS_EFFECTS),
                })
            return scenes

        # Auto-generate from filenames
        scenes = []
        for i, img_path in enumerate(images):
            narration = self._generate_scene_narration(img_path.name, topic)
            scenes.append({
                "image_path": img_path,
                "narration": narration,
                "duration": SCENE_DURATION_DEFAULT,
                "effect": KEN_BURNS_EFFECTS[i % len(KEN_BURNS_EFFECTS)],
            })
        return scenes

    def _generate_scene_narration(self, image_filename: str, topic: str) -> str:
        """Heuristic narration from filename + topic."""
        stem = Path(image_filename).stem.replace("_", " ").replace("-", " ")
        # Remove leading numeric prefixes like "01 "
        import re
        stem = re.sub(r"^\d+\s*", "", stem).strip()
        if not stem:
            stem = f"scene {image_filename}"
        return f"{stem}."

    def _generate_all_narrations(self, scenes: list[dict]) -> list[Path]:
        """Generate TTS audio for every scene, return list of wav paths."""
        paths: list[Path] = []
        for i, scene in enumerate(scenes):
            text = scene["narration"]
            if not text.strip():
                continue
            wav_path = self._temp_dir / f"narration_{i + 1:03d}.wav"
            generate_narration(text, wav_path)
            if wav_path.exists():
                paths.append(wav_path)
        return paths

    def _build_scene_clip(self, scene: dict):
        """Build a single video clip from a scene dict, applying Ken Burns."""
        img_path = scene["image_path"]
        duration = scene.get("duration", SCENE_DURATION_DEFAULT)
        effect = scene.get("effect", "zoom_in")

        clip = self._apply_ken_burns(img_path, duration, effect)
        clip = clip.with_effects([FadeIn(FADE_DURATION * 0.5), FadeOut(FADE_DURATION * 0.5)])
        return clip

    def _assemble_final(self, clips: list, audio_path: Path, output_path: Path):
        """Concatenate all clips, attach audio, and write MP4."""
        final = concatenate_videoclips(clips, method="compose")

        if audio_path.exists():
            try:
                audio_clip = AudioFileClip(str(audio_path))
                if audio_clip.duration > final.duration:
                    audio_clip = audio_clip.with_duration(final.duration)
                elif audio_clip.duration < final.duration:
                    from moviepy import AudioClip
                    silence = AudioClip(
                        lambda t: [0],
                        duration=final.duration - audio_clip.duration,
                        fps=22050,
                    )
                    from moviepy import concatenate_audioclips
                    audio_clip = concatenate_audioclips([audio_clip, silence])
                final = final.with_audio(audio_clip)
            except Exception as exc:
                print(f"[ImageToVideo] Audio attach failed ({exc}) — proceeding without audio")

        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=FPS,
            preset="medium",
            logger=None,
        )

        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass

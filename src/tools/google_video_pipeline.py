"""Full video pipeline using Google Vids/Flow for video + gTTS for narration + MoviePy for assembly."""

import json
from pathlib import Path
from datetime import datetime

from src.config import settings
from src.tools.account_tracker import (
    load_quotas, get_next_account, update_usage,
    check_quota_low, get_status_summary
)
from src.tools.tts_tools import generate_narration_segments, combine_audio_segments, add_background_music
from src.tools.notifier import send_quota_low_notification, send_quota_exhausted_notification


class GoogleVideoPipeline:
    """Orchestrates full video creation: script → video clips → narration → assembly."""

    def __init__(self):
        self.accounts = load_quotas()
        self._check_ollama()

    def _check_ollama(self):
        """Verify Ollama is available for script generation."""
        try:
            import requests
            resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if resp.status_code != 200:
                print("[Pipeline] Warning: Ollama not responding. Script generation will fail.")
        except Exception:
            print("[Pipeline] Warning: Ollama not available. Script generation will fail.")

    def create_video(
        self,
        topic: str,
        num_scenes: int = 12,
        scene_duration: int = 8,
        output_dir: Path | None = None,
    ) -> Path:
        """Run the full video creation pipeline.

        Args:
            topic: Video topic (e.g., "learn colors", "animal sounds")
            num_scenes: Number of scenes (each ~8 seconds)
            scene_duration: Duration per scene in seconds
            output_dir: Custom output directory

        Returns:
            Path to final assembled video
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir is None:
            output_dir = settings.VIDEOS_DIR / f"{topic.replace(' ', '_')}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  Google Video Pipeline")
        print(f"  Topic: {topic}")
        print(f"  Scenes: {num_scenes} x {scene_duration}s")
        print(f"  Output: {output_dir}")
        print(f"{'='*60}\n")

        # Step 1: Generate script
        print("[1/6] Generating script with Ollama...")
        scenes = self._generate_script(topic, num_scenes, scene_duration)
        if not scenes:
            print("[ERROR] Failed to generate script")
            return Path("")

        script_path = output_dir / "script.json"
        script_path.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
        print(f"  ✓ Script generated: {len(scenes)} scenes")

        # Step 2: Generate video clips
        print("\n[2/6] Generating video clips via Google Vids/Flow...")
        clips_dir = output_dir / "clips"
        clips_dir.mkdir(exist_ok=True)
        video_clips = self._generate_video_clips(scenes, clips_dir)
        print(f"  ✓ Generated {len(video_clips)} video clips")

        # Step 3: Generate narration
        print("\n[3/6] Generating narration with gTTS...")
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        narration_clips = self._generate_narration(scenes, audio_dir)
        print(f"  ✓ Generated {len(narration_clips)} narration clips")

        # Step 4: Combine narration
        print("\n[4/6] Combining narration...")
        combined_audio = audio_dir / "combined_narration.wav"
        if narration_clips:
            combine_audio_segments(narration_clips, combined_audio)
            print(f"  ✓ Narration combined: {combined_audio.name}")

            # Add background music
            mixed_audio = audio_dir / "final_audio.wav"
            add_background_music(combined_audio, mixed_audio)
            print(f"  ✓ Background music added")
        else:
            mixed_audio = None
            print("  ⚠ No narration to combine")

        # Step 5: Assemble final video
        print("\n[5/6] Assembling final video with MoviePy...")
        final_video = output_dir / f"{topic.replace(' ', '_')}_final.mp4"
        self._assemble_video(video_clips, mixed_audio, final_video)
        print(f"  ✓ Video assembled: {final_video.name}")

        # Step 6: Generate thumbnail
        print("\n[6/6] Generating thumbnail...")
        thumbnail = output_dir / "thumbnail.png"
        self._generate_thumbnail(topic, scenes, thumbnail)
        print(f"  ✓ Thumbnail generated")

        # Summary
        print(f"\n{'='*60}")
        print(f"  ✅ Video Complete!")
        print(f"  Video: {final_video}")
        print(f"  Thumbnail: {thumbnail}")
        print(f"  Script: {script_path}")
        print(f"{'='*60}\n")

        return final_video

    def _generate_script(self, topic: str, num_scenes: int, scene_duration: int) -> list[dict]:
        """Generate script using Ollama."""
        try:
            from langchain_ollama import OllamaLLM

            llm = OllamaLLM(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )

            prompt = f"""Generate a kids video script about "{topic}" with exactly {num_scenes} scenes.

Return ONLY valid JSON array, no other text. Each scene object must have:
- "scene_number": integer starting from 1
- "description": what happens in the scene (1-2 sentences)
- "narration": what the narrator says (simple, kid-friendly, 1-2 sentences)
- "duration_seconds": {scene_duration}
- "visual_prompt": detailed prompt for AI video generation (colorful, 3D cartoon style, kid-friendly)

Example format:
[
  {{
    "scene_number": 1,
    "description": "Red apples on a tree",
    "narration": "Look at the red apples on the tree!",
    "duration_seconds": {scene_duration},
    "visual_prompt": "A colorful animated red apple on a green tree, bright sunny day, 3D cartoon style, child-friendly"
  }}
]

Make it fun, educational, and engaging for toddlers (ages 1-4). Use simple words."""

            response = llm.invoke(prompt)

            # Extract JSON from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end > start:
                scenes = json.loads(response[start:end])
                return scenes

            print("[Pipeline] Warning: Could not parse Ollama response as JSON")
            return self._fallback_script(topic, num_scenes, scene_duration)

        except Exception as e:
            print(f"[Pipeline] Ollama error: {e}")
            return self._fallback_script(topic, num_scenes, scene_duration)

    def _fallback_script(self, topic: str, num_scenes: int, scene_duration: int) -> list[dict]:
        """Generate a basic fallback script when Ollama is unavailable."""
        scenes = []
        colors = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "brown"]

        for i in range(num_scenes):
            color = colors[i % len(colors)]
            scenes.append({
                "scene_number": i + 1,
                "description": f"A {color} object related to {topic}",
                "narration": f"Look! It's {color}! {topic} is so fun!",
                "duration_seconds": scene_duration,
                "visual_prompt": f"A colorful animated {color} object, {topic}, bright colors, 3D cartoon style, child-friendly, happy atmosphere"
            })

        return scenes

    def _generate_video_clips(self, scenes: list[dict], output_dir: Path) -> list[Path]:
        """Generate video clips via Google Vids/Flow."""
        clips = []

        for scene in scenes:
            account = get_next_account()
            if not account:
                print(f"  ⚠ No accounts with remaining quota!")
                # Try to create placeholder clips
                clip_path = output_dir / f"scene_{scene['scene_number']:03d}.mp4"
                self._create_placeholder_clip(scene, clip_path)
                clips.append(clip_path)
                continue

            clip_path = output_dir / f"scene_{scene['scene_number']:03d}.mp4"

            try:
                # TODO: Replace with actual Playwright automation
                # For now, create placeholder
                self._create_placeholder_clip(scene, clip_path)
                clips.append(clip_path)

                # Update usage
                update_usage(account["email"], "flow_daily", 1)
                update_usage(account["email"], "flow_monthly", 1)

                # Check if quota is low
                if check_quota_low(account["email"], settings.QUOTA_LOW_THRESHOLD):
                    send_quota_low_notification(
                        account["email"], "Google Flow",
                        remaining=f"{account.get('flow_monthly_used', 0)}/1500",
                        limit="1500"
                    )

                print(f"  ✓ Scene {scene['scene_number']} generated (account: {account['email'][:20]}...)")

            except Exception as e:
                print(f"  ✗ Scene {scene['scene_number']} failed: {e}")
                # Create placeholder on failure
                self._create_placeholder_clip(scene, clip_path)
                clips.append(clip_path)

        return clips

    def _create_placeholder_clip(self, scene: dict, output_path: Path):
        """Create a placeholder video clip using MoviePy (for testing)."""
        try:
            from moviepy import ColorClip, TextClip, CompositeVideoClip

            duration = scene.get("duration_seconds", 8)
            width, height = settings.VIDEO_RESOLUTION

            # Create colored background
            colors = [(255,100,100), (100,255,100), (100,100,255), (255,255,100), (255,100,255)]
            color = colors[scene["scene_number"] % len(colors)]
            bg = ColorClip(size=(width, height), color=color, duration=duration)

            # Add text
            txt = TextClip(
                text=f"Scene {scene['scene_number']}\n{scene['description'][:50]}",
                font_size=30,
                color="white",
                size=(width - 100, None),
                method="caption",
            ).with_duration(min(duration, 5)).with_position("center")

            video = CompositeVideoClip([bg, txt])
            video.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio=False,
                logger=None,
            )
            video.close()

        except Exception as e:
            # Absolute fallback: create empty file
            output_path.touch()
            print(f"  ⚠ Placeholder creation failed: {e}")

    def _generate_narration(self, scenes: list[dict], output_dir: Path) -> list[Path]:
        """Generate gTTS narration for each scene."""
        narration_data = []
        for scene in scenes:
            narration_data.append({
                "narration": scene.get("narration", ""),
                "duration_seconds": scene.get("duration_seconds", 8),
            })

        return generate_narration_segments(narration_data, output_dir, lang=settings.DEFAULT_LANGUAGE)

    def _assemble_video(self, video_clips: list[Path], audio_path: Path | None, output_path: Path):
        """Assemble video clips and audio into final video using MoviePy."""
        try:
            from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

            if not video_clips:
                print("  ⚠ No video clips to assemble")
                return

            # Load and concatenate video clips
            clips = []
            for clip_path in video_clips:
                if clip_path.exists() and clip_path.stat().st_size > 0:
                    try:
                        clip = VideoFileClip(str(clip_path))
                        clips.append(clip)
                    except Exception:
                        continue

            if not clips:
                print("  ⚠ No valid video clips found")
                return

            final_video = concatenate_videoclips(clips, method="compose")

            # Add audio if available
            if audio_path and audio_path.exists():
                try:
                    audio = AudioFileClip(str(audio_path))
                    # Trim audio to video length
                    if audio.duration > final_video.duration:
                        audio = audio.subclipped(0, final_video.duration)
                    elif audio.duration < final_video.duration:
                        # Video is longer, keep video as-is
                        pass
                    final_video = final_video.with_audio(audio)
                except Exception as e:
                    print(f"  ⚠ Could not add audio: {e}")

            # Write final video
            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac" if audio_path else None,
                logger=None,
            )

            # Clean up
            for clip in clips:
                clip.close()
            final_video.close()

        except Exception as e:
            print(f"  ⚠ Assembly error: {e}")
            # Create minimal output
            output_path.touch()

    def _generate_thumbnail(self, topic: str, scenes: list[dict], output_path: Path):
        """Generate a thumbnail using Pillow."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            width, height = 1280, 720
            img = Image.new("RGB", (width, height), color=(30, 30, 60))
            draw = ImageDraw.Draw(img)

            # Draw gradient-like background with circles
            import random
            random.seed(hash(topic))
            for _ in range(20):
                x = random.randint(0, width)
                y = random.randint(0, height)
                r = random.randint(30, 120)
                color = (
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255),
                )
                draw.ellipse([x - r, y - r, x + r, y + r], fill=color + (80,), outline=None)

            # Add text
            try:
                font_large = ImageFont.truetype("arial.ttf", 60)
                font_small = ImageFont.truetype("arial.ttf", 30)
            except Exception:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # Title
            title = topic.title()
            bbox = draw.textbbox((0, 0), title, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, 280), title, fill="white", font=font_large)

            # Subtitle
            subtitle = f"{len(scenes)} scenes of fun!"
            bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
            sub_width = bbox2[2] - bbox2[0]
            draw.text(((width - sub_width) // 2, 360), subtitle, fill=(200, 200, 200), font=font_small)

            img.save(str(output_path), "PNG")

        except Exception as e:
            print(f"  ⚠ Thumbnail generation failed: {e}")

    def get_status(self) -> str:
        """Get current pipeline status."""
        return get_status_summary()


def run_pipeline(topic: str, num_scenes: int = 12, scene_duration: int = 8) -> Path:
    """Convenience function to run the pipeline."""
    pipeline = GoogleVideoPipeline()
    return pipeline.create_video(topic, num_scenes, scene_duration)


if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "learn colors"
    run_pipeline(topic)

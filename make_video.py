"""Complete Video Creation Workflow using Bing Image Creator images.

Usage:
    python make_video.py --topic "learn colors"
    python make_video.py --topic "animal sounds" --assemble
    python make_video.py --topic "learn colors" --images-dir C:\\Users\\khali\\Pictures\\ai_images

Steps:
    1. Generates prompts for Bing Image Creator
    2. You create images at https://www.bing.com/create
    3. Download images to input_images/ folder
    4. Run again with --assemble to create video
"""

import argparse
import json
import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from pydub import AudioSegment
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

load_dotenv()

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.config import settings
from src.tools.tts_tools import generate_narration, combine_audio_segments

console = Console()

# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------

TOPIC_PROMPT_BANK: dict[str, list[dict]] = {
    "learn colors": [
        {"desc": "A bright red apple on a wooden table", "narration": "Red! This apple is red."},
        {"desc": "A shiny blue ball in green grass", "narration": "Blue! The ball is blue."},
        {"desc": "A bright yellow sun in a blue sky", "narration": "Yellow! The sun is yellow."},
        {"desc": "A lush green tree with brown trunk", "narration": "Green! The tree is green."},
        {"desc": "An orange pumpkin on hay", "narration": "Orange! The pumpkin is orange."},
        {"desc": "A purple bunch of grapes", "narration": "Purple! The grapes are purple."},
        {"desc": "A pink flamingo standing by a lake", "narration": "Pink! The flamingo is pink."},
        {"desc": "A white snowman with a red scarf", "narration": "White! The snowman is white."},
        {"desc": "A brown teddy bear on a rug", "narration": "Brown! The teddy bear is brown."},
        {"desc": "A rainbow over a green hill", "narration": "A rainbow has many colors!"},
        {"desc": "A box of colorful crayons on paper", "narration": "So many colors to choose!"},
        {"desc": "A child holding a colorful paint palette", "narration": "Colors are wonderful!"},
    ],
    "animal sounds": [
        {"desc": "A cute brown cow on a green farm", "narration": "The cow says moo!"},
        {"desc": "A fluffy white sheep in a meadow", "narration": "The sheep says baa!"},
        {"desc": "A yellow chick pecking on the ground", "narration": "The chick says peep!"},
        {"desc": "A black and white cat with green eyes", "narration": "The cat says meow!"},
        {"desc": "A brown puppy wagging its tail", "narration": "The puppy says woof!"},
        {"desc": "A white duck swimming in a pond", "narration": "The duck says quack!"},
        {"desc": "A gray horse galloping in a field", "narration": "The horse says neigh!"},
        {"desc": "A brown owl sitting on a tree branch", "narration": "The owl says hoot!"},
        {"desc": "A green frog on a lily pad", "narration": "The frog says ribbit!"},
        {"desc": "A large gray elephant spraying water", "narration": "The elephant says trumpets!"},
        {"desc": "A colorful parrot on a perch", "narration": "The parrot says squawk!"},
        {"desc": "All the animals together on a farm", "narration": "Animals make fun sounds!"},
    ],
    "counting numbers": [
        {"desc": "A single bright red balloon floating up", "narration": "One! One red balloon."},
        {"desc": "Two cute yellow ducks swimming together", "narration": "Two! Two yellow ducks."},
        {"desc": "Three colorful balloons tied together", "narration": "Three! Three balloons."},
        {"desc": "Four green frogs on a lily pad", "narration": "Four! Four green frogs."},
        {"desc": "Five orange stars in a dark sky", "narration": "Five! Five orange stars."},
        {"desc": "Six blue fish swimming in the ocean", "narration": "Six! Six blue fish."},
        {"desc": "Seven red ladybugs on a leaf", "narration": "Seven! Seven ladybugs."},
        {"desc": "Eight yellow rubber ducks in a row", "narration": "Eight! Eight rubber ducks."},
        {"desc": "Nine colorful flowers in a garden", "narration": "Nine! Nine pretty flowers."},
        {"desc": "Ten bright candles on a birthday cake", "narration": "Ten! Ten candles!"},
        {"desc": "A child counting on fingers happily", "narration": "Counting from one to ten!"},
        {"desc": "Numbers 1 through 10 floating in the air", "narration": "Numbers are fun to learn!"},
    ],
    "shapes": [
        {"desc": "A bright red circle like a ball", "narration": "This is a circle! Round and round."},
        {"desc": "A blue square like a box", "narration": "This is a square! Four equal sides."},
        {"desc": "A green triangle like a mountain", "narration": "This is a triangle! Three sides."},
        {"desc": "A yellow rectangle like a door", "narration": "This is a rectangle! Two long sides."},
        {"desc": "A purple star sparkling in the sky", "narration": "This is a star! Twinkle twinkle."},
        {"desc": "An orange heart on a pink background", "narration": "This is a heart! For love."},
        {"desc": "A brown oval like an egg", "narration": "This is an oval! Like an egg."},
        {"desc": "A blue diamond on a card", "narration": "This is a diamond! Four points."},
        {"desc": "A green pentagon on grass", "narration": "This is a pentagon! Five sides."},
        {"desc": "A rainbow with many shapes around it", "narration": "So many shapes in our world!"},
        {"desc": "A child holding shape blocks", "narration": "Shapes are everywhere!"},
        {"desc": "All shapes floating together in the sky", "narration": "Let's learn more shapes together!"},
    ],
}

PROMPT_TEMPLATE = (
    "A colorful 3D cartoon illustration for kids, {description}, "
    "bright vivid colors, child-friendly style, no text, clean background, "
    "high quality, Pixar style animation"
)


def generate_prompts(topic: str) -> list[dict]:
    """Generate 12 prompts with narrations for the given topic.

    Uses a built-in bank for known topics, otherwise generates generic prompts.
    Returns list of dicts with keys: prompt, narration, scene_id.
    """
    topic_lower = topic.lower().strip()
    scene_data = TOPIC_PROMPT_BANK.get(topic_lower)

    if not scene_data:
        # Generic fallback — derive scene descriptions from topic words
        words = topic_lower.split()
        keywords = [
            "happy children", "colorful classroom", "friendly animals",
            "bright playground", "sunny day", "rainbow in the sky",
            "fun learning", "beautiful nature", "cheerful friends",
            "magic garden", "sparkling stars", "wonderful world",
        ]
        scene_data = []
        for i in range(12):
            kw = keywords[i % len(keywords)]
            scene_data.append({
                "desc": f"A cheerful illustration of {kw} related to {topic}",
                "narration": f"Scene {i + 1}: Let's learn about {topic}!",
            })

    scenes = []
    for i, item in enumerate(scene_data):
        prompt = PROMPT_TEMPLATE.format(description=item["desc"])
        scenes.append({
            "scene_id": i + 1,
            "prompt": prompt,
            "narration": item["narration"],
            "description": item["desc"],
        })
    return scenes


def save_prompts(scenes: list[dict], topic: str, output_dir: Path) -> Path:
    """Save prompts to a text file for the user."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    filepath = output_dir / f"prompts_{slug}.txt"

    lines = [
        f"=== Bing Image Creator Prompts for: {topic} ===",
        f"Go to: https://www.bing.com/create",
        "",
    ]
    for scene in scenes:
        lines.append(f"--- Scene {scene['scene_id']} ---")
        lines.append(f"Prompt: {scene['prompt']}")
        lines.append(f"Narration: {scene['narration']}")
        lines.append("")

    lines.append("After generating, download images and name them: scene_001.png, scene_002.png, ...")
    lines.append(f"Place them in: {output_dir.parent / 'input_images'}")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

def collect_images(images_dir: Path, expected: int = 12) -> list[Path]:
    """Collect and sort images from the input directory."""
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    images = sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in exts and p.is_file()
    )
    if not images:
        return []
    return images[:expected]


def resize_image(img_path: Path, width: int, height: int, output_path: Path) -> Path:
    """Resize an image to target dimensions, center-cropping as needed."""
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
    return output_path


# ---------------------------------------------------------------------------
# Video assembly
# ---------------------------------------------------------------------------

def create_scene_clip(
    image_path: Path,
    audio_path: Path | None,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
    extra_padding: float = 0.5,
) -> Path:
    """Create a video clip from a single image + audio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine duration from audio
    duration = 5.0
    if audio_path and audio_path.exists():
        try:
            audio_seg = AudioSegment.from_wav(str(audio_path))
            duration = len(audio_seg) / 1000.0 + extra_padding
        except Exception:
            pass

    # Use ffmpeg to create clip from image
    try:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-t", f"{duration:.2f}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(fps),
            "-preset", "ultrafast",
        ]
        if audio_path and audio_path.exists():
            cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-b:a", "128k"])
        cmd.append(str(output_path))

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0 and output_path.exists():
            return output_path
    except Exception:
        pass

    # Fallback: MoviePy
    try:
        from moviepy import ImageClip, AudioFileClip

        clip = ImageClip(str(image_path), duration=duration).with_fps(fps)
        if audio_path and audio_path.exists():
            try:
                audio_clip = AudioFileClip(str(audio_path))
                if audio_clip.duration > duration:
                    audio_clip = audio_clip.with_duration(duration)
                clip = clip.with_audio(audio_clip)
            except Exception:
                pass

        clip.write_videofile(
            str(output_path), codec="libx264", fps=fps,
            preset="ultrafast", logger=None,
        )
        clip.close()
        return output_path
    except Exception:
        pass

    return output_path


def concatenate_clips(clip_paths: list[Path], output_path: Path) -> Path:
    """Concatenate multiple video clips into one."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(clip_paths) == 1:
        # Just copy
        import shutil
        shutil.copy2(str(clip_paths[0]), str(output_path))
        return output_path

    # ffmpeg concat demuxer
    list_file = output_path.parent / "_concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p}'" for p in clip_paths),
        encoding="utf-8",
    )

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(output_path),
            ],
            capture_output=True,
            timeout=300,
        )
        if result.returncode == 0 and output_path.exists():
            list_file.unlink(missing_ok=True)
            return output_path
    except Exception:
        pass

    # Fallback: MoviePy
    try:
        from moviepy import VideoFileClip, concatenate_videoclips

        clips = [VideoFileClip(str(p)) for p in clip_paths]
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(output_path), codec="libx264", fps=settings.FPS,
            preset="ultrafast", logger=None,
        )
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        return output_path
    except Exception:
        pass

    list_file.unlink(missing_ok=True)
    return output_path


def assemble_video(
    scenes: list[dict],
    images_dir: Path,
    topic: str,
    output_dir: Path,
) -> Path | None:
    """Full assembly pipeline: narration -> clips -> final video."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")

    width, height = settings.VIDEO_RESOLUTION
    fps = settings.FPS

    images = collect_images(images_dir)
    if not images:
        console.print("[red]No images found in input_images/![/red]")
        return None

    console.print(f"[green]Found {len(images)} images[/green]")

    # --- Step 1: Generate narration audio ---
    console.print("\n[bold cyan]Step 1: Generating narration...[/bold cyan]")
    audio_dir = output_dir / "audio" / slug
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_paths: list[Path] = []

    for i, scene in enumerate(scenes[: len(images)]):
        text = scene.get("narration", "")
        if not text.strip():
            continue
        wav_path = audio_dir / f"narration_{i + 1:03d}.wav"
        if not wav_path.exists():
            generate_narration(text, wav_path)
        if wav_path.exists():
            audio_paths.append(wav_path)
            console.print(f"  [dim]{wav_path.name}[/dim]")

    # --- Step 2: Prepare images ---
    console.print("\n[bold cyan]Step 2: Preparing images...[/bold cyan]")
    prepared_dir = output_dir / "prepared" / slug
    prepared_dir.mkdir(parents=True, exist_ok=True)
    prepared_images: list[Path] = []

    for i, img_path in enumerate(images[: len(scenes)]):
        out = prepared_dir / f"scene_{i + 1:03d}.png"
        resize_image(img_path, width, height, out)
        prepared_images.append(out)
        console.print(f"  [dim]{img_path.name} -> {out.name}[/dim]")

    # --- Step 3: Create scene clips ---
    console.print("\n[bold cyan]Step 3: Creating scene clips...[/bold cyan]")
    clips_dir = output_dir / "clips" / slug
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_paths: list[Path] = []

    for i, img_path in enumerate(prepared_images):
        audio_path = audio_paths[i] if i < len(audio_paths) else None
        clip_path = clips_dir / f"scene_{i + 1:03d}.mp4"
        if not clip_path.exists():
            create_scene_clip(img_path, audio_path, clip_path, width, height, fps)
        if clip_path.exists():
            clip_paths.append(clip_path)
            console.print(f"  [dim]{clip_path.name}[/dim]")

    if not clip_paths:
        console.print("[red]No clips were created![/red]")
        return None

    # --- Step 4: Combine into final video ---
    console.print("\n[bold cyan]Step 4: Assembling final video...[/bold cyan]")
    final_path = output_dir / "videos" / f"{slug}.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    concatenate_clips(clip_paths, final_path)

    # --- Step 5: Combine audio tracks ---
    console.print("\n[bold cyan]Step 5: Combining audio...[/bold cyan]")
    if audio_paths:
        combined_audio = output_dir / "audio" / f"{slug}_combined.wav"
        combine_audio_segments(audio_paths, combined_audio)
        console.print(f"  [dim]Audio: {combined_audio.name}[/dim]")

    return final_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kids Video Creator — Bing Image Creator workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python make_video.py --topic "learn colors"
  python make_video.py --topic "animal sounds" --assemble
  python make_video.py --topic "counting numbers" --images-dir ./my_images
        """,
    )
    parser.add_argument(
        "--topic", "-t",
        default="learn colors",
        help="Video topic (default: learn colors)",
    )
    parser.add_argument(
        "--assemble", "-a",
        action="store_true",
        help="Skip prompt generation, assemble video from existing images",
    )
    parser.add_argument(
        "--images-dir", "-i",
        type=str,
        default=None,
        help="Path to folder containing downloaded images (skips prompt generation)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=str(ROOT / "output"),
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--scenes", "-n",
        type=int,
        default=12,
        help="Number of scenes (default: 12)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open Bing Image Creator in browser",
    )
    return parser


def print_banner():
    console.print()
    console.print(
        Panel.fit(
            "[bold magenta]Kids Video Creator[/bold magenta]\n"
            "[dim]Bing Image Creator + Video Assembly Pipeline[/dim]",
            border_style="bright_blue",
        )
    )


def print_scenes_table(scenes: list[dict]):
    table = Table(title="Generated Prompts", show_lines=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Prompt", style="white", max_width=70)
    table.add_column("Narration", style="green", max_width=40)

    for scene in scenes:
        table.add_row(
            str(scene["scene_id"]),
            scene["prompt"][:70] + ("..." if len(scene["prompt"]) > 70 else ""),
            scene["narration"],
        )
    console.print(table)


def main():
    print_banner()

    parser = build_parser()
    args = parser.parse_args()

    topic = args.topic.strip()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scenes = generate_prompts(topic)
    scenes = scenes[: args.scenes]

    # --- Determine mode ---
    skip_prompts = args.assemble or args.images_dir is not None

    if not skip_prompts:
        # Mode 1: Generate prompts
        console.print(f"\n[bold]Topic:[/bold] {topic}")
        console.print(f"[bold]Scenes:[/bold] {len(scenes)}\n")

        print_scenes_table(scenes)

        # Save prompts
        prompts_file = save_prompts(scenes, topic, output_dir / "prompts")
        console.print(f"\n[green]Prompts saved to:[/green] {prompts_file}")

        # Open browser
        if not args.no_browser:
            if Confirm.ask("\n[bold]Open Bing Image Creator in browser?[/bold]", default=True):
                webbrowser.open("https://www.bing.com/create")
                console.print("[dim]Opened https://www.bing.com/create[/dim]")

        # Instructions
        console.print(
            Panel(
                "[bold yellow]Next Steps:[/bold yellow]\n\n"
                f"1. Go to [link]https://www.bing.com/create[/link]\n"
                f"2. Generate each image using the prompts above\n"
                f"3. Download images and name them: scene_001.png, scene_002.png, ...\n"
                f"4. Place them in: [cyan]{output_dir.parent / 'input_images'}[/cyan]\n"
                f"5. Run: [bold]python make_video.py --topic \"{topic}\" --assemble[/bold]",
                title="Instructions",
                border_style="bright_green",
            )
        )
        return

    # --- Assemble mode ---
    images_dir = Path(args.images_dir) if args.images_dir else ROOT / "input_images"

    if not images_dir.exists():
        console.print(f"[red]Images directory not found: {images_dir}[/red]")
        console.print(
            f"[yellow]Create it and place your scene images there.[/yellow]\n"
            f"  mkdir \"{images_dir}\""
        )
        sys.exit(1)

    images = collect_images(images_dir)
    if not images:
        console.print(f"[red]No images found in {images_dir}[/red]")
        console.print("[yellow]Expected files: scene_001.png, scene_002.png, ...[/yellow]")
        sys.exit(1)

    console.print(f"[bold]Topic:[/bold] {topic}")
    console.print(f"[bold]Images:[/bold] {len(images)} in {images_dir}")
    console.print(f"[bold]Scenes:[/bold] {len(scenes)}\n")

    final = assemble_video(scenes, images_dir, topic, output_dir)

    if final and final.exists():
        size_mb = final.stat().st_size / (1024 * 1024)
        console.print(
            Panel(
                f"[bold green]Video created![/bold green]\n\n"
                f"File: [cyan]{final}[/cyan]\n"
                f"Size: {size_mb:.1f} MB\n"
                f"Duration: ~{len(scenes) * 5} seconds",
                title="Done",
                border_style="bright_green",
            )
        )
    else:
        console.print("[red]Video creation failed. Check errors above.[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

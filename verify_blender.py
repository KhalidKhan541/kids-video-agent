"""Verify Blender installation and render a test scene.

Run:  python verify_blender.py

This will check if Blender is installed, report its version,
and generate a simple test animation to confirm rendering works.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.tools.blender_tools import verify_blender, render_script, find_blender
from src.templates.blender.scene_generators import generate_simple_scene
from src.config import settings


def main():
    print("=" * 60)
    print("  🎬 Kids Video Agent — Blender Setup Verification")
    print("=" * 60)

    # Step 1: Find Blender
    print("\n📌 Step 1: Locating Blender...")
    info = verify_blender()
    blender_path = find_blender()

    if info["available"]:
        print(f"  ✅ Found: {info['version']}")
        print(f"  📁 Path: {info['path']}")
    else:
        print(f"  ❌ Blender not found at: {settings.BLENDER_EXECUTABLE}")
        print(f"  🔍 Searched common locations and PATH.")
        print(f"\n  💡 Install Blender from: https://www.blender.org/download/")
        print(f"  Then set BLENDER_EXECUTABLE in your .env file, e.g.:")
        print(f"     BLENDER_EXECUTABLE=C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe")
        return

    # Step 2: Generate a test script
    print("\n📌 Step 2: Generating test scene script...")
    test_scene = {
        "scene_id": 1,
        "description": "Test scene",
        "lyrics_section": "Twinkle twinkle little star",
        "duration_seconds": 5,
    }
    test_config = {
        "scene_type": "simple",
        "color_theme": ["pastel_blue", "soft_yellow", "pink"],
        "character_count": 2,
        "background_music": False,
        "duration_seconds": 5,
        "resolution": (1920, 1080),
        "fps": 24,
    }
    test_proj = {
        "rhyme_name": "Test Rhyme",
        "language": "en",
    }

    script = generate_simple_scene(test_scene, test_config, test_proj, 0)
    script_path = settings.SCRIPTS_DIR / "test_blender_scene.py"
    script_path.write_text(script, encoding="utf-8")
    print(f"  ✅ Script written: {script_path.name} ({len(script)} chars)")

    # Step 3: Render the test scene
    print("\n📌 Step 3: Rendering test scene (5 seconds)...")
    print("  ⏳ This may take a minute for Blender to start...")

    output_path = settings.RENDERS_DIR / "test_blender_render.mp4"
    result = render_script(script_path, output_path, timeout=120)

    if result["success"]:
        size = Path(output_path).stat().st_size / 1024 / 1024 if Path(output_path).exists() else 0
        print(f"  ✅ Render complete! Output: {output_path.name} ({size:.1f} MB)")
        print(f"\n  🎉 Blender integration is working!")
    else:
        print(f"  ⚠️  Render had issues: {result.get('error', 'unknown')[:100]}")
        if result.get("stderr"):
            print(f"  Stderr: {result['stderr'][:200]}")

    print("\n📌 Step 4: Checking ffmpeg for video composition...")
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"  ✅ ffmpeg found: {ffmpeg}")
    else:
        print(f"  ⚠️  ffmpeg not found. Install from: https://ffmpeg.org/")
        print(f"     Without ffmpeg, video composition will use moviepy fallback.")

    print("\n" + "=" * 60)
    if info["available"]:
        print("  ✅ Blender is ready for video generation!")
    print("=" * 60)


if __name__ == "__main__":
    main()

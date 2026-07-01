"""Orchestrator - Coordinates all agents using free tools (Groq, Pollinations, Piper, Pixabay, FFmpeg)."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()

try:
    import imageio_ffmpeg
    _ff = Path(imageio_ffmpeg.get_ffmpeg_exe())
    if str(_ff.parent) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(_ff.parent) + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent


def _print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def run_pipeline(
    topic: str,
    num_scenes: int = 12,
    lang: str = "en",
    output_root: Path | None = None,
    skip_images: bool = False,
    skip_music: bool = False,
    **kwargs,
) -> dict[str, Any]:
    if output_root is None:
        output_root = BASE_DIR / "output"
    output_root.mkdir(parents=True, exist_ok=True)

    slug = topic.lower().strip().replace(" ", "_")
    job_dir = output_root / slug
    job_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "pipeline": "Kids Video Pipeline (Free Stack)",
        "topic": topic,
        "started_at": datetime.now().isoformat(),
        "agents": {},
        "status": "running",
    }

    # Agent 1: Script Generation (Groq)
    _print("\n" + "=" * 60)
    _print("[Agent 1/6] ScriptWriter - Generating script via Groq")
    _print("=" * 60)
    t1 = time.time()
    try:
        from src.tools.groq_tools import generate_script
        script_result = generate_script(topic, language=lang, num_scenes=num_scenes)
        results["agents"]["ScriptWriter"] = script_result
        scenes = script_result.get("scenes", [])
        _print(f"  [OK] {len(scenes)} scenes generated in {time.time() - t1:.1f}s")
        _print(f"  [TITLE] {script_result.get('title', 'N/A')}")
    except Exception as e:
        results["agents"]["ScriptWriter"] = {"error": str(e)}
        results["status"] = "failed"
        _print(f"  [FAIL] ScriptWriter failed: {e}")
        return _finalize(results, job_dir)

    script_file = job_dir / "script.json"
    script_file.write_text(json.dumps(script_result, indent=2, default=str), encoding="utf-8")

    # Agent 2: Image Generation (Pollinations.ai)
    _print("\n" + "=" * 60)
    _print("[Agent 2/6] ImageGenerator - Generating images via Pollinations.ai")
    _print("=" * 60)
    t2 = time.time()
    images_dir = job_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    if skip_images:
        results["agents"]["ImageGenerator"] = {"skipped": True}
        _print("  [SKIP] Skipped")
    else:
        try:
            from src.tools.image_tools import generate_batch
            prompts = [s.get("image_prompt", s.get("description", "")) for s in scenes]
            image_paths = generate_batch(prompts, output_dir=str(images_dir))
            results["agents"]["ImageGenerator"] = {
                "success_count": len(image_paths),
                "total": len(prompts),
                "paths": image_paths,
            }
            _print(f"  [OK] {len(image_paths)}/{len(prompts)} images in {time.time() - t2:.1f}s")
        except Exception as e:
            results["agents"]["ImageGenerator"] = {"error": str(e)}
            _print(f"  [WARN] ImageGenerator failed: {e}")

    # Agent 3: Voice Narration (Piper TTS)
    _print("\n" + "=" * 60)
    _print("[Agent 3/6] VoiceNarrator - Generating voice via Piper TTS")
    _print("=" * 60)
    t3 = time.time()
    audio_dir = job_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    try:
        from src.tools.piper_tts_tools import generate_narration_segments
        segments = [{"text": s.get("narration", s.get("narration_text", "")), "filename": f"scene_{s['scene_id']:03d}.wav"} for s in scenes]
        audio_files = generate_narration_segments(segments, output_dir=str(audio_dir), lang=lang)
        results["agents"]["VoiceNarrator"] = {"count": len(audio_files), "files": audio_files}
        _print(f"  [OK] {len(audio_files)} narrations in {time.time() - t3:.1f}s")
    except Exception as e:
        results["agents"]["VoiceNarrator"] = {"error": str(e)}
        _print(f"  [WARN] VoiceNarrator failed: {e}")

    # Agent 4: Background Music (Pixabay)
    _print("\n" + "=" * 60)
    _print("[Agent 4/6] MusicAgent - Searching Pixabay for background music")
    _print("=" * 60)
    t4 = time.time()
    music_path = None
    if skip_music:
        results["agents"]["MusicAgent"] = {"skipped": True}
        _print("  [SKIP] Skipped")
    else:
        try:
            from src.tools.music_tools import get_kids_bgm
            music_path = get_kids_bgm(output_dir=job_dir / "music")
            results["agents"]["MusicAgent"] = {"path": str(music_path) if music_path else None, "success": bool(music_path)}
            _print(f"  [OK] Music downloaded in {time.time() - t4:.1f}s")
        except Exception as e:
            results["agents"]["MusicAgent"] = {"error": str(e)}
            _print(f"  [WARN] MusicAgent failed: {e}")

    # Agent 5: Video Composition (FFmpeg)
    _print("\n" + "=" * 60)
    _print("[Agent 5/6] VideoComposer - Assembling video with FFmpeg")
    _print("=" * 60)
    t5 = time.time()
    try:
        from src.tools.ffmpeg_tools import compose_final
        video_path = job_dir / f"{slug}.mp4"
        narration_files = sorted(audio_dir.glob("*.wav")) if audio_dir.exists() else []
        narration_str = str(narration_files[0]) if narration_files else ""
        rc = compose_final(
            images=[str(p) for p in sorted(images_dir.glob("*.png"))],
            audio=narration_str,
            music=str(music_path) if music_path else None,
            output_path=str(video_path),
        )
        if rc == 0:
            size_mb = video_path.stat().st_size / 1024 / 1024
            _print(f"  [OK] Video created: {video_path} ({size_mb:.1f} MB)")
            results["agents"]["VideoComposer"] = {"success": True, "path": str(video_path)}
            results["final_video"] = str(video_path)
        else:
            _print(f"  [FAIL] VideoComposer failed with code {rc}")
            results["agents"]["VideoComposer"] = {"success": False, "error": f"FFmpeg exit code {rc}"}
    except Exception as e:
        results["agents"]["VideoComposer"] = {"error": str(e)}
        _print(f"  [FAIL] VideoComposer failed: {e}")

    # Agent 6: SEO Metadata (Groq)
    _print("\n" + "=" * 60)
    _print("[Agent 6/6] SEOOptimizer - Generating metadata via Groq")
    _print("=" * 60)
    t6 = time.time()
    try:
        from src.tools.groq_tools import generate_seo
        seo_result = generate_seo(topic)
        results["agents"]["SEOOptimizer"] = seo_result
        _print(f"  [OK] SEO metadata generated in {time.time() - t6:.1f}s")
        _print(f"  [META] Title: {seo_result.get('title', 'N/A')}")
    except Exception as e:
        results["agents"]["SEOOptimizer"] = {"error": str(e)}
        _print(f"  [WARN] SEOOptimizer failed: {e}")

    results["status"] = "completed"
    results["completed_at"] = datetime.now().isoformat()
    _print("\n" + "=" * 60)
    _print("[DONE] Pipeline Complete!")
    if results.get("final_video"):
        _print(f"  [VIDEO] {results['final_video']}")
    _print(f"  [OUTPUT] {job_dir}")
    _print("=" * 60)

    # Agent 7: Email Notification
    _print("\n" + "=" * 60)
    _print("[Agent 7/7] EmailNotifier - Sending completion email")
    _print("=" * 60)
    try:
        from src.tools.email_tools import send_video_notification
        seo = results.get("agents", {}).get("SEOOptimizer", {})
        email_result = send_video_notification(
            topic=topic,
            video_path=results.get("final_video", ""),
            title=seo.get("title", topic),
            description=seo.get("description", ""),
            tags=seo.get("tags", []),
            pipeline_report=results,
        )
        results["agents"]["EmailNotifier"] = email_result
        if email_result.get("success"):
            _print(f"  [OK] Email sent to {email_result.get('sent_to', 'N/A')}")
        else:
            _print(f"  [WARN] Email failed: {email_result.get('error', 'unknown')}")
    except Exception as e:
        results["agents"]["EmailNotifier"] = {"error": str(e)}
        _print(f"  [WARN] EmailNotifier failed: {e}")

    _save_results(results, job_dir)
    return results


def _finalize(results: dict, job_dir: Path) -> dict:
    results["completed_at"] = datetime.now().isoformat()
    _save_results(results, job_dir)
    return results


def _save_results(results: dict, job_dir: Path):
    report_path = job_dir / "pipeline_report.json"
    report_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

#!/usr/bin/env python3
"""Kids Video Agent - 8-Agent Pipeline CLI"""

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agents.orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Kids Video Agent - 8-Agent Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run_pipeline.py --topic "learn colors"
  python run_pipeline.py --topic "animal sounds" --lang en
  python run_pipeline.py --topic "counting numbers" --skip-images --skip-music
        """,
    )
    parser.add_argument("--topic", "-t", default="learn colors", help="Video topic")
    parser.add_argument("--scenes", "-n", type=int, default=12, help="Number of scenes")
    parser.add_argument("--lang", "-l", default="en", help="Language code (en, hi, ur)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output directory")
    parser.add_argument("--skip-images", action="store_true", help="Skip image generation")
    parser.add_argument("--skip-music", action="store_true", help="Skip background music")

    args = parser.parse_args()

    output_root = Path(args.output) if args.output else None

    results = run_pipeline(
        topic=args.topic,
        num_scenes=args.scenes,
        lang=args.lang,
        output_root=output_root,
        skip_images=args.skip_images,
        skip_music=args.skip_music,
    )

    if results.get("status") == "failed":
        print(f"\n[FAIL] Pipeline failed. Check {results.get('agents', {})} for details.")
        sys.exit(1)

    final_video = results.get("final_video", "")
    if final_video:
        print(f"\n[OK] Video ready: {final_video}")


if __name__ == "__main__":
    main()

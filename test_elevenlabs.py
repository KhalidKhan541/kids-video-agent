"""Quick test script for ElevenLabs TTS integration with gTTS fallback."""

import os
from pathlib import Path

from src.tools.tts_tools import generate_narration


def main():
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    if not api_key:
        print("=" * 60)
        print("ELEVENLABS_API_KEY is not set!")
        print()
        print("To use ElevenLabs TTS:")
        print("  1. Go to https://elevenlabs.io and sign up (free tier available)")
        print("  2. Go to Profile Settings > API Key and copy your key")
        print("  3. Set it in your environment:")
        print("     set ELEVENLABS_API_KEY=your_key_here")
        print("  4. Or add it to your .env file:")
        print("     ELEVENLABS_API_KEY=your_key_here")
        print()
        print("Proceeding with gTTS fallback...")
        print("=" * 60)
    else:
        print(f"ELEVENLABS_API_KEY detected: {api_key[:4]}...{api_key[-4:]}")

    output_path = Path("output/test_elevenlabs.wav")
    test_text = "Hello kids! Welcome to our channel!"

    print(f"\nGenerating test narration: \"{test_text}\"")
    print(f"Output: {output_path}\n")

    try:
        result = generate_narration(test_text, output_path)
        if result.exists():
            size_kb = result.stat().st_size / 1024
            print(f"SUCCESS: Audio saved to {result} ({size_kb:.1f} KB)")
        else:
            print(f"FAILURE: Expected output at {result} but file not found")
    except Exception as e:
        print(f"FAILURE: Exception during generation: {e}")


if __name__ == "__main__":
    main()

"""Piper TTS tools for high-quality local text-to-speech generation.

Falls back to gTTS (Google Text-to-Speech) when Piper is unavailable.
"""

import subprocess
import sys
import os
import json
import shutil
from pathlib import Path
from typing import List, Optional

PIPER_AVAILABLE = None  # Cached check result


def _check_piper_available() -> bool:
    """Check if piper-tts is available."""
    global PIPER_AVAILABLE
    if PIPER_AVAILABLE is not None:
        return PIPER_AVAILABLE
    try:
        result = subprocess.run(
            [sys.executable, "-m", "piper_tts", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        PIPER_AVAILABLE = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        PIPER_AVAILABLE = False
    return PIPER_AVAILABLE


def _generate_gtts_fallback(text: str, output_path: str, lang: str = "en") -> str:
    """Generate audio using gTTS as fallback when Piper is unavailable."""
    from gtts import gTTS
    import io
    from pydub import AudioSegment

    tts = gTTS(text=text, lang=lang, slow=False)
    mp3_buffer = io.BytesIO()
    tts.write_to_fp(mp3_buffer)
    mp3_buffer.seek(0)

    audio = AudioSegment.from_mp3(mp3_buffer)
    audio.export(output_path, format="wav")
    return output_path

PIPER_DIR = Path.home() / ".cache" / "piper"
MODELS_DIR = PIPER_DIR / "models"

AVAILABLE_VOICES = {
    "en": ["en_US-amy-medium", "en_US-lessac-medium", "en_US-libritts_r-medium"],
    "es": ["es_ES-davefx-medium", "es_ES-sharvard-medium"],
    "fr": ["fr_FR-siwis-medium", "fr_FR-tom-medium"],
    "hi": ["hi_IN-swara-medium"],
}


def ensure_piper_installed() -> str:
    """Ensure piper-tts is installed and return the piper command path."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "piper_tts", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return sys.executable
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "piper-tts"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return sys.executable


def download_voice_model(voice: str) -> Path:
    """Download a voice model if not already present."""
    model_dir = MODELS_DIR / voice
    model_file = model_dir / f"{voice}.onnx"
    config_file = model_dir / f"{voice}.onnx.json"

    if model_file.exists() and config_file.exists():
        return model_file

    model_dir.mkdir(parents=True, exist_ok=True)

    base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
    onnx_url = f"{base_url}/{voice}.onnx"
    config_url = f"{base_url}/{voice}.onnx.json"

    lang_parts = voice.split("_")
    lang_prefix = lang_parts[0]
    country = lang_parts[1] if len(lang_parts) > 1 else ""
    variant = voice.split("-")[-1] if "-" in voice else "medium"
    name = voice.split("-")[1] if "-" in voice else country

    base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_prefix}/{country}/{name}/{variant}"

    for url, dest in [(onnx_url, model_file), (config_url, config_file)]:
        try:
            subprocess.check_call(
                ["curl", "-L", "-o", str(dest), url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            if dest.exists():
                dest.unlink()
            raise RuntimeError(f"Failed to download voice model: {voice}")

    return model_file


def generate_narration(
    text: str,
    output_path: str,
    voice: str = "en_US-amy-medium",
    length_scale: float = 1.0,
    noise_scale: float = 0.667,
    noise_w: float = 0.8,
    lang: str = "en",
) -> str:
    """Generate WAV audio narration from text.

    Tries Piper TTS first, falls back to gTTS if Piper is unavailable.

    Args:
        text: The text to synthesize.
        output_path: Path for the output WAV file.
        voice: Voice model name (e.g., en_US-amy-medium).
        length_scale: Speech rate (1.0 = normal, >1 = slower, <1 = faster).
        noise_scale: Noise for phoneme generation.
        noise_w: Phoneme noise width.
        lang: Language code for gTTS fallback (e.g., 'en', 'hi', 'ur').

    Returns:
        Path to the generated WAV file.
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Try Piper TTS first
    if _check_piper_available():
        try:
            python_path = ensure_piper_installed()
            model_path = download_voice_model(voice)

            cmd = [
                python_path,
                "-m",
                "piper_tts",
                "--model",
                str(model_path),
                "--output_file",
                str(output),
                "--length_scale",
                str(length_scale),
                "--noise_scale",
                str(noise_scale),
                "--noise_w",
                str(noise_w),
            ]

            process = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if process.returncode == 0 and output.exists():
                return str(output)
            else:
                print(f"[Piper TTS] Failed (exit code {process.returncode}), falling back to gTTS")
        except Exception as e:
            print(f"[Piper TTS] Error: {e}, falling back to gTTS")
    else:
        print("[Piper TTS] Not available, using gTTS fallback")

    # Fallback to gTTS
    return _generate_gtts_fallback(text, str(output), lang=lang)


def generate_narration_segments(
    segments: List[dict],
    output_dir: str,
    voice: str = "en_US-amy-medium",
    sample_rate: int = 22050,
    lang: str = "en",
) -> List[str]:
    """Generate narration for multiple segments/scenes.

    Args:
        segments: List of dicts with 'text' and 'filename' keys.
        output_dir: Directory to save generated audio files.
        voice: Voice model name.
        sample_rate: Output sample rate (default 22050).
        lang: Language code for gTTS fallback (e.g., 'en', 'hi', 'ur').

    Returns:
        List of paths to generated WAV files.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for i, segment in enumerate(segments):
        text = segment.get("text", "")
        filename = segment.get("filename", f"segment_{i:03d}.wav")

        if not text.strip():
            print(f"Warning: Skipping empty segment {i}")
            continue

        if not filename.endswith(".wav"):
            filename += ".wav"

        file_path = output_path / filename

        try:
            result = generate_narration(
                text=text,
                output_path=str(file_path),
                voice=voice,
                lang=lang,
            )
            generated_files.append(result)
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating segment {i}: {e}")
            continue

    return generated_files


def list_voices(language: Optional[str] = None) -> dict:
    """List available voices.

    Args:
        language: Optional language code to filter (en, es, fr, hi).

    Returns:
        Dictionary mapping language codes to voice names.
    """
    if language:
        if language not in AVAILABLE_VOICES:
            return {language: []}
        return {language: AVAILABLE_VOICES[language]}

    return AVAILABLE_VOICES


def get_installed_voices() -> List[str]:
    """List locally downloaded voice models."""
    if not MODELS_DIR.exists():
        return []

    installed = []
    for item in MODELS_DIR.iterdir():
        if item.is_dir():
            onnx_files = list(item.glob("*.onnx"))
            if onnx_files:
                installed.append(item.name)

    return installed


def remove_voice_model(voice: str) -> bool:
    """Remove a downloaded voice model."""
    model_dir = MODELS_DIR / voice
    if model_dir.exists():
        shutil.rmtree(model_dir)
        return True
    return False

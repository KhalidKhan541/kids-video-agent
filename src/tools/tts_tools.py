"""Audio generation using ElevenLabs (primary) or gTTS (fallback) for narration.
Background music generation using Google Lyria 3 (Gemini Music Generator).
"""

import wave
import math
import struct
import os
import random
import tempfile
from pathlib import Path

from pydub import AudioSegment


def _get_gemini_client():
    """Get Gemini client if API key is available."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        return None
    except Exception:
        return None


def generate_lyria_bgm(prompt: str, output_path: Path, duration_seconds: int = 30) -> Path:
    """Generate background music using Google Lyria 3.

    Args:
        prompt: Text description of the music to generate
        output_path: Where to save the generated audio
        duration_seconds: Duration in seconds (max 30 for clip model)

    Returns:
        Path to the generated audio file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = _get_gemini_client()
    if not client:
        print("[Lyria] No GEMINI_API_KEY found, cannot generate music")
        return None

    try:
        # Use Lyria 3 Clip model for 30-second clips
        response = client.models.generate_content(
            model="lyria-3-clip-preview",
            contents=prompt
        )

        # Parse response for audio data
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                # Save the audio data
                audio_data = part.inline_data.data
                temp_mp3 = output_path.with_suffix(".mp3")

                with open(str(temp_mp3), "wb") as f:
                    f.write(audio_data)

                # Convert to WAV if needed
                if output_path.suffix.lower() == ".wav":
                    audio_segment = AudioSegment.from_mp3(str(temp_mp3))
                    audio_segment = audio_segment.set_channels(1).set_frame_rate(44100)
                    audio_segment.export(str(output_path), format="wav")
                    temp_mp3.unlink()
                else:
                    temp_mp3.rename(output_path)

                print(f"[Lyria] Generated music: {output_path}")
                return output_path

        print("[Lyria] No audio data in response")
        return None

    except Exception as e:
        print(f"[Lyria] Error generating music: {e}")
        return None


def generate_kids_bgm(output_path: Path, duration_ms: int = 30000) -> Path:
    """Generate kid-friendly background music using Lyria 3.

    Args:
        output_path: Where to save the generated audio
        duration_ms: Duration in milliseconds

    Returns:
        Path to the generated audio file, or None if failed
    """
    # Kid-friendly music prompt
    prompt = (
        "A cheerful, upbeat children's background music track. "
        "Happy xylophone melody with light percussion and soft piano chords. "
        "Playful, innocent, and joyful mood perfect for a kids educational video. "
        "No vocals, instrumental only. Bright and colorful sound."
    )

    return generate_lyria_bgm(prompt, output_path, duration_seconds=30)


def _get_elevenlabs_client():
    """Get ElevenLabs client if API key is available."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        return None
    try:
        from elevenlabs.client import ElevenLabs
        return ElevenLabs(api_key=api_key)
    except ImportError:
        return None


def _get_elevenlabs_voice_id():
    """Get configured ElevenLabs voice ID."""
    return os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


def generate_narration(text: str, output_path: Path, lang: str = "en", slow: bool = False) -> Path:
    """Generate speech audio from text using ElevenLabs (preferred) or gTTS (fallback).

    Args:
        text: The text to narrate
        output_path: Where to save the WAV file
        lang: Language code (en, hi, ur, etc.)
        slow: Whether to speak slowly (gTTS only)

    Returns:
        Path to the generated WAV file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try ElevenLabs first
    client = _get_elevenlabs_client()
    if client:
        try:
            return _generate_elevenlabs(text, output_path, client)
        except Exception as e:
            print(f"[TTS] ElevenLabs failed ({e}), falling back to gTTS")

    # Fallback to gTTS
    return _generate_gtts(text, output_path, lang, slow)


def _generate_elevenlabs(text: str, output_path: Path, client) -> Path:
    """Generate audio using ElevenLabs API."""
    temp_mp3 = output_path.with_suffix(".mp3")
    voice_id = _get_elevenlabs_voice_id()

    audio = client.generate(
        text=text,
        voice=voice_id,
        model="eleven_turbo_v2_5",
    )

    # Save to temp MP3
    with open(str(temp_mp3), "wb") as f:
        for chunk in audio:
            f.write(chunk)

    # Convert MP3 to WAV
    audio_segment = AudioSegment.from_mp3(str(temp_mp3))
    audio_segment = audio_segment.set_channels(1).set_frame_rate(22050)
    audio_segment.export(str(output_path), format="wav")

    # Clean up temp MP3
    try:
        temp_mp3.unlink()
    except Exception:
        pass

    return output_path


def _generate_gtts(text: str, output_path: Path, lang: str = "en", slow: bool = False) -> Path:
    """Generate audio using gTTS (fallback)."""
    from gtts import gTTS

    temp_mp3 = output_path.with_suffix(".mp3")

    try:
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(temp_mp3))

        audio = AudioSegment.from_mp3(str(temp_mp3))
        audio = audio.set_channels(1).set_frame_rate(22050)
        audio.export(str(output_path), format="wav")

        try:
            temp_mp3.unlink()
        except Exception:
            pass

        return output_path

    except Exception:
        duration = max(5, min(30, len(text) // 4))
        _write_silence_wav(output_path, duration)
        return output_path


def generate_narration_segments(
    segments: list[dict],
    output_dir: Path,
    lang: str = "en",
) -> list[Path]:
    """Generate narration for multiple segments (scenes).

    Args:
        segments: List of dicts with 'narration' and 'duration_seconds'
        output_dir: Directory for output files
        lang: Language code

    Returns:
        List of paths to generated audio files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    client = _get_elevenlabs_client()
    provider = "ElevenLabs" if client else "gTTS"
    print(f"[TTS] Using {provider} for narration")

    for i, seg in enumerate(segments):
        text = seg.get("narration", "")
        if not text.strip():
            continue

        audio_path = output_dir / f"narration_{i+1:03d}.wav"
        generate_narration(text, audio_path, lang=lang)
        if audio_path.exists():
            paths.append(audio_path)

    return paths


def add_background_music(
    narration_path: Path,
    output_path: Path,
    music_volume: float = 0.15,
    fade_duration: int = 2000,
) -> Path:
    """Mix narration with background music generated by Lyria 3.

    Args:
        narration_path: Path to narration WAV
        output_path: Path to save mixed audio
        music_volume: Volume of background music (0.0 - 1.0)
        fade_duration: Fade in/out duration in ms

    Returns:
        Path to mixed audio
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        narration = AudioSegment.from_wav(str(narration_path))
    except Exception:
        _write_silence_wav(output_path, 30)
        return output_path

    # Generate background music with Lyria
    temp_bgm = output_path.parent / "temp_lyria_bgm.wav"
    bgm_path = generate_kids_bgm(temp_bgm, duration_ms=len(narration) + 2000)

    if bgm_path and bgm_path.exists():
        try:
            bgm = AudioSegment.from_wav(str(bgm_path))
            # Loop or trim to match narration length
            if len(bgm) < len(narration):
                # Loop the BGM
                loops_needed = (len(narration) // len(bgm)) + 1
                bgm = bgm * loops_needed
            bgm = bgm[:len(narration) + 1000]  # Trim to narration length + 1s

            bgm = bgm - (20 - int(music_volume * 40))
            bgm = bgm.fade_in(fade_duration).fade_out(fade_duration)

            mixed = bgm.overlay(narration, position=0)
            mixed.export(str(output_path), format="wav")

            # Clean up temp file
            try:
                temp_bgm.unlink()
            except Exception:
                pass

            return output_path
        except Exception as e:
            print(f"[TTS] Error mixing Lyria BGM: {e}")

    # Fallback to silence if Lyria fails
    print("[TTS] Lyria failed, using silence as background")
    _write_silence_wav(output_path, len(narration) // 1000)
    return output_path


def combine_audio_segments(
    audio_paths: list[Path],
    output_path: Path,
    gap_ms: int = 500,
) -> Path:
    """Combine multiple audio segments into one continuous track.

    Args:
        audio_paths: List of audio file paths
        output_path: Where to save combined audio
        gap_ms: Silence between segments in milliseconds

    Returns:
        Path to combined audio
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined = AudioSegment.empty()

    silence = AudioSegment.silent(duration=gap_ms)

    for i, path in enumerate(audio_paths):
        try:
            segment = AudioSegment.from_wav(str(path))
            combined += segment
            if i < len(audio_paths) - 1:
                combined += silence
        except Exception:
            continue

    if len(combined) == 0:
        _write_silence_wav(output_path, 30)
        return output_path

    combined.export(str(output_path), format="wav")
    return output_path


def _generate_bgm_segment(duration_ms: int) -> AudioSegment:
    """Generate cheerful, kid-friendly background music with rich harmonics."""
    sample_rate = 44100
    duration_s = duration_ms / 1000.0
    num_samples = int(sample_rate * duration_s)

    # Major scale frequencies (C major pentatonic for happy sound)
    melody_notes = [262, 294, 330, 392, 440, 523, 587, 659]
    bass_notes = [131, 147, 165, 196, 220, 262]

    # Chord progression: C - Am - F - G (happy kids progression)
    chords = [
        ([262, 330, 392], [131]),      # C major
        ([220, 262, 330], [110]),      # A minor
        ([175, 220, 262], [87]),       # F major
        ([196, 247, 294], [98]),       # G major
        ([262, 330, 392], [131]),      # C major
        ([220, 262, 330], [110]),      # A minor
        ([175, 220, 262], [87]),       # F major
        ([196, 247, 294], [98]),       # G major
    ]

    chord_duration = int(num_samples / len(chords))
    eighth = chord_duration // 8  # Eighth note timing

    def pluck(freq, t, duration=0.1):
        """Karplus-Strong-like plucked string synthesis."""
        if freq == 0:
            return 0
        decay = math.exp(-t * 8.0)
        val = 0
        # Fundamental
        val += 0.5 * math.sin(2 * math.pi * freq * t) * decay
        # 2nd harmonic
        val += 0.3 * math.sin(2 * math.pi * freq * 2 * t) * math.exp(-t * 12)
        # 3rd harmonic
        val += 0.15 * math.sin(2 * math.pi * freq * 3 * t) * math.exp(-t * 16)
        # Slight noise for attack
        if t < 0.01:
            val += 0.2 * (2 * (hash(str(int(t * 1000))) % 1000) / 1000 - 1) * (1 - t / 0.01)
        return val

    def pad(freq, t):
        """Soft pad/synth sound."""
        if freq == 0:
            return 0
        val = 0.3 * math.sin(2 * math.pi * freq * t)
        val += 0.15 * math.sin(2 * math.pi * freq * 1.001 * t)  # Chorus
        val += 0.1 * math.sin(2 * math.pi * freq * 0.999 * t)   # Detune
        val += 0.2 * math.sin(2 * math.pi * freq * 2 * t)       # Octave
        return val

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        chord_idx = min(i // chord_duration, len(chords) - 1)
        notes, bass = chords[chord_idx]
        pos_in_chord = i % chord_duration

        val = 0

        # Melody - arpeggiated plucked notes
        eighth_idx = pos_in_chord // eighth
        melody_freq = melody_notes[(chord_idx * 2 + eighth_idx) % len(melody_notes)]
        note_t = (pos_in_chord % eighth) / sample_rate
        if note_t < 0.3:
            val += pluck(melody_freq, note_t) * 0.25

        # Pad chords
        for n in notes:
            val += pad(n, t) * 0.08

        # Bass - simple pattern
        bass_freq = bass[0]
        bass_pos = pos_in_chord / chord_duration
        if bass_pos < 0.5:
            val += pluck(bass_freq, bass_pos) * 0.2
        else:
            val += pluck(bass_freq * 1.5, bass_pos) * 0.15

        # Light percussion - kick on beat 1 and 3, hi-hat on all beats
        beat_pos = (pos_in_chord % eighth) / eighth
        beat_idx = pos_in_chord // eighth
        if beat_pos < 0.05:  # Kick
            kick_t = beat_pos
            val += 0.15 * math.sin(2 * math.pi * 60 * kick_t) * math.exp(-kick_t * 40)
        if beat_idx % 2 == 0 and beat_pos < 0.02:  # Hi-hat
            val += 0.05 * (random.random() * 2 - 1)

        # Gentle volume envelope
        chord_pos = pos_in_chord / chord_duration
        env = 0.6 + 0.4 * math.sin(math.pi * chord_pos)
        val *= env

        val = max(-0.85, min(0.85, val))
        samples.append(int(val * 32767))

    temp_path = Path("temp_bgm.wav")
    with wave.open(str(temp_path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    audio = AudioSegment.from_wav(str(temp_path))

    try:
        temp_path.unlink()
    except Exception:
        pass

    return audio


def _write_silence_wav(path: Path, duration: int = 30, sample_rate: int = 22050):
    """Write a silent WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = sample_rate * duration
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for _ in range(0, num_samples, 1024):
            chunk = min(1024, num_samples - _)
            wf.writeframes(struct.pack(f"<{chunk}h", *([0] * chunk)))

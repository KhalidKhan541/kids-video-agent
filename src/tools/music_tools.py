"""Background music tools using Pixabay Videos API.

Downloads audio from Pixabay video clips (free, royalty-free).
Falls back to synthesized music if no videos found.
"""

import hashlib
import math
import os
import struct
import subprocess
import wave
import json
from pathlib import Path
from typing import Optional

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "music_cache"


def _get_api_key() -> str:
    key = os.getenv("PIXABAY_API_KEY", "")
    if not key:
        raise RuntimeError("PIXABAY_API_KEY not set. Get a free key at https://pixabay.com/api/docs/")
    return key


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _find_ffmpeg() -> Optional[str]:
    for name in ("ffmpeg", "ffmpeg.exe"):
        try:
            result = subprocess.run([name, "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return None


def _find_ffprobe() -> Optional[str]:
    for name in ("ffprobe", "ffprobe.exe"):
        try:
            result = subprocess.run([name, "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _get_audio_duration(audio_path: Path, ffprobe: str) -> float:
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration", "-of", "json", str(audio_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except Exception:
        pass
    return 0.0


def search_music(query: str = "kids background music", limit: int = 5) -> list[dict]:
    api_key = _get_api_key()
    try:
        params = {
            "key": api_key,
            "q": query,
            "video_type": "film",
            "per_page": min(limit, 20),
            "safesearch": "true",
        }
        resp = requests.get("https://pixabay.com/api/videos/", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for hit in data.get("hits", []):
            videos = hit.get("videos", {})
            medium = videos.get("medium", {})
            url = medium.get("url", "")
            if url:
                results.append({
                    "id": hit.get("id"),
                    "title": hit.get("tags", "Unknown"),
                    "url": url,
                    "duration": hit.get("duration", 0),
                    "user": hit.get("user", ""),
                    "downloads": hit.get("downloads", 0),
                })

        print(f"[Music] Found {len(results)} video clips for '{query}'")
        return results
    except Exception as e:
        print(f"[Music] Search failed: {e}")
        return []


def download_and_extract_audio(video_url: str, output_path: Path) -> Optional[Path]:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print("[Music] FFmpeg not found")
        return None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_video = output_path.parent / f"_temp_{output_path.stem}.mp4"

    try:
        print(f"[Music] Downloading video: {video_url}")
        resp = requests.get(video_url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(str(temp_video), "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[Music] Extracting audio...")
        cmd = [ffmpeg, "-y", "-i", str(temp_video), "-vn", "-acodec", "libmp3lame", "-q:a", "4", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        temp_video.unlink(missing_ok=True)

        if result.returncode == 0 and output_path.exists():
            print(f"[Music] Saved: {output_path}")
            return output_path
        else:
            print(f"[Music] FFmpeg error: {result.stderr[:300]}")
            return None
    except Exception as e:
        temp_video.unlink(missing_ok=True)
        print(f"[Music] Download/extract failed: {e}")
        return None


def get_kids_bgm(output_dir: Path, query: str = "happy children cartoon background", use_cache: bool = True) -> Optional[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    results = search_music(query, limit=5)
    if not results:
        results = search_music("instrumental", limit=5)

    if results:
        best = max(results, key=lambda x: x.get("downloads", 0))
        output_path = output_dir / f"bgm_{best['id']}.mp3"

        if use_cache:
            key = _cache_key(best["url"])
            cached = cache_dir / f"{key}.mp3"
            if cached.exists():
                import shutil
                shutil.copy2(str(cached), str(output_path))
                print(f"[Music] Using cached: {cached.name}")
                return output_path

        path = download_and_extract_audio(best["url"], output_path)
        if path and use_cache:
            try:
                import shutil
                key = _cache_key(best["url"])
                shutil.copy2(str(path), str(cache_dir / f"{key}.mp3"))
            except Exception:
                pass
        return path

    print("[Music] No videos found, generating synthesized BGM")
    return _synthesize_kids_music(output_dir / "bgm_synthesized.wav", duration_ms=60000)


def loop_music(music_path: Path, target_duration: float, output_path: Path, fade_out_ms: int = 2000) -> Optional[Path]:
    ffmpeg = _find_ffmpeg()
    ffprobe = _find_ffprobe()
    if not ffmpeg:
        return None

    music_path = Path(music_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if ffprobe:
        duration = _get_audio_duration(music_path, ffprobe)
        if duration > 0:
            loops = max(1, int(target_duration / duration) + 1)
            cmd = [ffmpeg, "-stream_loop", str(loops), "-i", str(music_path),
                   "-t", f"{target_duration:.2f}",
                   "-af", f"afade=t=out:st={max(0, target_duration - fade_out_ms / 1000):.2f}:d={fade_out_ms / 1000:.2f}",
                   "-y", str(output_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return output_path

    try:
        import shutil
        shutil.copy2(str(music_path), str(output_path))
        return output_path
    except Exception:
        return None


def _synthesize_kids_music(output_path: Path, duration_ms: int = 60000) -> Optional[Path]:
    SAMPLE_RATE = 44100
    duration_s = duration_ms / 1000.0
    num_samples = int(SAMPLE_RATE * duration_s)

    melody_notes = [262, 294, 330, 392, 440, 523, 587, 659]
    chords = [
        ([262, 330, 392], [131]), ([220, 262, 330], [110]),
        ([175, 220, 262], [87]), ([196, 247, 294], [98]),
        ([262, 330, 392], [131]), ([220, 262, 330], [110]),
        ([175, 220, 262], [87]), ([196, 247, 294], [98]),
    ]

    chord_duration = num_samples // len(chords)
    eighth = chord_duration // 8

    def _pluck(freq, t):
        if freq == 0: return 0
        decay = math.exp(-t * 8.0)
        val = 0.5 * math.sin(2 * math.pi * freq * t) * decay
        val += 0.3 * math.sin(2 * math.pi * freq * 2 * t) * math.exp(-t * 12)
        val += 0.15 * math.sin(2 * math.pi * freq * 3 * t) * math.exp(-t * 16)
        return val

    def _pad(freq, t):
        if freq == 0: return 0
        val = 0.3 * math.sin(2 * math.pi * freq * t)
        val += 0.15 * math.sin(2 * math.pi * freq * 1.001 * t)
        val += 0.1 * math.sin(2 * math.pi * freq * 0.999 * t)
        return val

    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        chord_idx = min(i // chord_duration, len(chords) - 1)
        notes, bass = chords[chord_idx]
        pos = i % chord_duration

        val = 0
        eighth_idx = pos // eighth
        melody_freq = melody_notes[(chord_idx * 2 + eighth_idx) % len(melody_notes)]
        note_t = (pos % eighth) / SAMPLE_RATE
        if note_t < 0.3:
            val += _pluck(melody_freq, note_t) * 0.25
        for n in notes:
            val += _pad(n, t) * 0.08
        bass_pos = pos / chord_duration
        if bass_pos < 0.5:
            val += _pluck(bass[0], bass_pos) * 0.2
        else:
            val += _pluck(bass[0] * 1.5, bass_pos) * 0.15
        beat_pos = (pos % eighth) / eighth
        if beat_pos < 0.05:
            val += 0.15 * math.sin(2 * math.pi * 60 * beat_pos) * math.exp(-beat_pos * 40)
        val *= 0.6 + 0.4 * math.sin(math.pi * pos / chord_duration)
        val = max(-0.85, min(0.85, val))
        samples.append(int(val * 32767))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    print(f"[Music] Synthesized {duration_ms/1000:.0f}s BGM: {output_path}")
    return output_path


def clear_cache(cache_dir: Optional[Path] = None) -> int:
    cache_dir = Path(cache_dir or CACHE_DIR)
    if not cache_dir.exists():
        return 0
    count = 0
    for f in cache_dir.iterdir():
        if f.is_file():
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
    print(f"[Music] Cleared {count} cached files")
    return count

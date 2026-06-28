"""FFmpeg-based video composition tools for kids video agent.

All video composition is done via FFmpeg subprocess calls.
No GPU acceleration required.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.environ.get("FFPROBE_BIN", "ffprobe")


class FFmpegError(Exception):
    """Raised when an FFmpeg command fails."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def _run(cmd: List[str], description: str = "ffmpeg") -> subprocess.CompletedProcess:
    """Run a subprocess command and raise FFmpegError on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise FFmpegError(
                f"{description} failed (exit code {result.returncode})",
                returncode=result.returncode,
                stderr=result.stderr[-2000:] if result.stderr else "",
            )
        return result
    except FileNotFoundError:
        raise FFmpegError(
            f"{FFMPEG_BIN} not found. Ensure FFmpeg is installed and on PATH.",
            returncode=-1,
        )
    except subprocess.TimeoutExpired:
        raise FFmpegError(f"{description} timed out after 600s", returncode=-1)


def _probe(path: str) -> dict:
    """Probe a media file and return format/stream info."""
    cmd = [
        FFPROBE_BIN,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    import json
    result = _run(cmd, f"ffprobe {path}")
    return json.loads(result.stdout)


def _get_duration(path: str) -> float:
    """Get duration of a media file in seconds."""
    info = _probe(path)
    return float(info["format"].get("duration", 0))


def ken_burns(
    image_path: str,
    output_path: str,
    duration: float = 5,
    zoom_speed: float = 0.0015,
    fps: int = 30,
    resolution: Tuple[int, int] = (1920, 1080),
) -> int:
    """Animate a static image with Ken Burns zoom/pan effect.

    Args:
        image_path: Path to input image.
        output_path: Path to output video.
        duration: Duration of output clip in seconds.
        zoom_speed: Zoom rate per frame (0.0015 = slow zoom in).
        fps: Output frame rate.
        resolution: Output width x height.

    Returns:
        Exit code (0 = success).
    """
    w, h = resolution
    total_frames = int(duration * fps)

    # Zoompan filter: slow zoom from center
    # z: zoom level, x/y: top-left corner position
    zoompan = (
        f"zoompan=z='min(zoom+{zoom_speed},1.5)'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={total_frames}:s={w}x{h}:fps={fps}"
    )

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", zoompan,
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        str(output_path),
    ]

    try:
        _run(cmd, f"ken_burns({image_path})")
        return 0
    except FFmpegError as e:
        print(f"[ken_burns] Error: {e}\n{e.stderr}")
        return e.returncode


def add_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    volume: float = 1.0,
) -> int:
    """Mux audio onto a video file.

    Args:
        video_path: Path to input video.
        audio_path: Path to input audio.
        output_path: Path to output video.
        volume: Audio volume multiplier (1.0 = unchanged).

    Returns:
        Exit code (0 = success).
    """
    vol_filter = f"volume={volume}" if volume != 1.0 else None
    audio_opts = ["-i", str(audio_path)]
    if vol_filter:
        audio_opts += ["-af", vol_filter]

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        *audio_opts,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    try:
        _run(cmd, f"add_audio({video_path}, {audio_path})")
        return 0
    except FFmpegError as e:
        print(f"[add_audio] Error: {e}\n{e.stderr}")
        return e.returncode


def add_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
    font_size: int = 24,
    font_color: str = "white",
    outline_color: str = "black",
    outline_width: int = 2,
    margin_v: int = 30,
) -> int:
    """Burn subtitles into a video using ASS/SRT filter.

    Args:
        video_path: Path to input video.
        srt_path: Path to SRT subtitle file.
        output_path: Path to output video.
        font_size: Subtitle font size.
        font_color: Subtitle font color (white, yellow, etc.).
        outline_color: Text outline color.
        outline_width: Text outline thickness in pixels.
        margin_v: Vertical margin from bottom.

    Returns:
        Exit code (0 = success).
    """
    # Escape special characters for FFmpeg filter
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")
    force_style = (
        f"FontSize={font_size},"
        f"PrimaryColour=&H00FFFFFF,"  # ASS color format
        f"OutlineColour=&H00000000,"
        f"Outline={outline_width},"
        f"MarginV={margin_v}"
    )

    vf = f"subtitles='{srt_escaped}':force_style='{force_style}'"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        str(output_path),
    ]

    try:
        _run(cmd, f"add_subtitles({video_path})")
        return 0
    except FFmpegError as e:
        print(f"[add_subtitles] Error: {e}\n{e.stderr}")
        return e.returncode


def crossfade_clips(
    clips: List[str],
    output_path: str,
    fade_duration: float = 1.0,
) -> int:
    """Join video clips with crossfade transitions.

    Joins clips sequentially with a crossfade between each pair.

    Args:
        clips: List of video file paths.
        output_path: Path to output video.
        fade_duration: Duration of each crossfade in seconds.

    Returns:
        Exit code (0 = success).

    Raises:
        ValueError: If fewer than 1 clip provided.
    """
    if not clips:
        print("[crossfade_clips] Error: no clips provided")
        return 1
    if len(clips) == 1:
        # Single clip, just copy
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", str(clips[0]),
            "-c", "copy",
            str(output_path),
        ]
        try:
            _run(cmd, "crossfade_clips(copy single)")
            return 0
        except FFmpegError as e:
            print(f"[crossfade_clips] Error: {e}\n{e.stderr}")
            return e.returncode

    # Build xfade filter chain for multiple clips
    # FFmpeg xfade syntax: xfade=transition=fade:duration=D:offset=T
    inputs = []
    for clip in clips:
        inputs += ["-i", str(clip)]

    # Get durations to calculate offsets
    durations = [_get_duration(c) for c in clips]

    # Build filter complex
    filter_parts = []
    n = len(clips)
    current_offset = durations[0] - fade_duration

    if n == 2:
        vf = (
            f"[0:v][1:v]xfade=transition=fade"
            f":duration={fade_duration}"
            f":offset={current_offset}[vout]"
        )
    else:
        # Chain xfade filters: each crossfade takes previous output
        # First xfade
        parts = []
        prev_label = "0:v"
        for i in range(1, n):
            offset = sum(durations[:i]) - i * fade_duration
            next_label = f"v{i}" if i < n - 1 else "vout"
            parts.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade"
                f":duration={fade_duration}"
                f":offset={offset:.3f}[{next_label}]"
            )
            prev_label = next_label
        vf = ";".join(parts)

    # Audio crossfade: use acrossfade for pairs, or amerge
    af_parts = []
    n_audio = len(clips)
    if n_audio == 2:
        af = (
            f"[0:a][1:a]acrossfade=d={fade_duration}:c1=tri:c2=tri[aout]"
        )
    else:
        # Chain acrossfade filters
        a_parts = []
        prev_label = "0:a"
        for i in range(1, n_audio):
            next_label = f"a{i}" if i < n_audio - 1 else "aout"
            a_parts.append(
                f"[{prev_label}][{i}:a]acrossfade=d={fade_duration}"
                f":c1=tri:c2=tri[{next_label}]"
            )
            prev_label = next_label
        af = ";".join(a_parts)

    filter_complex = vf + ";" + af

    cmd = [
        FFMPEG_BIN,
        "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ]

    try:
        _run(cmd, f"crossfade_clips({len(clips)} clips)")
        return 0
    except FFmpegError as e:
        print(f"[crossfade_clips] Error: {e}\n{e.stderr}")
        return e.returncode


def generate_srt(
    segments: List[dict],
    output_path: str,
) -> int:
    """Generate an SRT subtitle file from timed segments.

    Args:
        segments: List of dicts with keys:
            - text: str (subtitle text)
            - start: float (start time in seconds)
            - end: float (end time in seconds)
        output_path: Path to write the SRT file.

    Returns:
        Exit code (0 = success).
    """

    def _format_time(seconds: float) -> str:
        """Format seconds to SRT timestamp HH:MM:SS,mmm."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                f.write(f"{i}\n")
                f.write(f"{_format_time(seg['start'])} --> {_format_time(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")
        return 0
    except (KeyError, IOError) as e:
        print(f"[generate_srt] Error: {e}")
        return 1


def compose_final(
    images: List[str],
    audio: str,
    music: Optional[str],
    output_path: str,
    narration_volume: float = 1.0,
    music_volume: float = 0.15,
    narration_duration: Optional[float] = None,
    fps: int = 30,
    resolution: Tuple[int, int] = (1920, 1080),
) -> int:
    """Create the final video from images, narration audio, and background music.

    Workflow:
    1. Generate Ken Burns clips for each image (auto-timed to narration).
    2. Concatenate clips with crossfade transitions.
    3. Overlay narration audio.
    4. Mix in background music at reduced volume.

    Args:
        images: List of image file paths (one per scene).
        audio: Path to narration audio file.
        music: Optional path to background music file.
        output_path: Path to final output video.
        narration_volume: Narration volume multiplier.
        music_volume: Background music volume (0.0-1.0, default 0.15).
        narration_duration: Override narration duration. Auto-detected if None.
        fps: Output frame rate.
        resolution: Output resolution (width, height).

    Returns:
        Exit code (0 = success).
    """
    if not images:
        print("[compose_final] Error: no images provided")
        return 1

    with tempfile.TemporaryDirectory(prefix="ffmpeg_tools_") as tmpdir:
        clips: List[str] = []

        # Determine per-image duration
        if narration_duration is None:
            narration_duration = _get_duration(audio)

        per_image_duration = narration_duration / len(images)

        # Step 1: Generate Ken Burns clips
        for i, img in enumerate(images):
            clip_path = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
            rc = ken_burns(
                img, clip_path,
                duration=per_image_duration,
                fps=fps,
                resolution=resolution,
            )
            if rc != 0:
                print(f"[compose_final] ken_burns failed for image {i}")
                return rc
            clips.append(clip_path)

        # Step 2: Crossfade clips together
        concatenated = os.path.join(tmpdir, "concatenated.mp4")
        fade_dur = min(0.5, per_image_duration / 4)
        rc = crossfade_clips(clips, concatenated, fade_duration=fade_dur)
        if rc != 0:
            print("[compose_final] crossfade_clips failed")
            return rc

        # Step 3: Add narration audio
        with_narration = os.path.join(tmpdir, "with_narration.mp4")
        rc = add_audio(
            concatenated, audio, with_narration,
            volume=narration_volume,
        )
        if rc != 0:
            print("[compose_final] add_audio(narration) failed")
            return rc

        # Step 4: Mix in background music if provided
        if music and os.path.exists(music):
            # Use amix or amerge to combine narration + music
            music_dur = _get_duration(music)
            cmd = [
                FFMPEG_BIN,
                "-y",
                "-i", str(with_narration),
                "-stream_loop", "-1",  # loop music if shorter than video
                "-i", str(music),
                "-filter_complex",
                (
                    f"[0:a]volume={narration_volume}[narr];"
                    f"[1:a]volume={music_volume},afade=t=out:st={narration_duration - 2}:d=2[bg];"
                    f"[narr][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                ),
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-t", str(narration_duration),
                str(output_path),
            ]
            try:
                _run(cmd, "compose_final(mix music)")
                return 0
            except FFmpegError as e:
                print(f"[compose_final] music mix failed: {e}\n{e.stderr}")
                # Fall through: copy narration-only version
                import shutil
                shutil.copy2(with_narration, output_path)
                return 0
        else:
            # No music, just copy narration version
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", str(with_narration),
                "-c", "copy",
                str(output_path),
            ]
            try:
                _run(cmd, "compose_final(copy)")
                return 0
            except FFmpegError as e:
                print(f"[compose_final] copy failed: {e}\n{e.stderr}")
                return e.returncode


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.tools.ffmpeg_tools <command> [args...]")
        print("Commands: ken_burns, add_audio, add_subtitles, crossfade_clips, generate_srt, compose_final")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    dispatch = {
        "ken_burns": lambda: print(f"Exit: {ken_burns(args[0], args[1], float(args[2]) if len(args) > 2 else 5)}"),
        "add_audio": lambda: print(f"Exit: {add_audio(args[0], args[1], args[2])}") if len(args) >= 3 else print("Usage: add_audio <video> <audio> <output>"),
        "add_subtitles": lambda: print(f"Exit: {add_subtitles(args[0], args[1], args[2])}") if len(args) >= 3 else print("Usage: add_subtitles <video> <srt> <output>"),
        "crossfade_clips": lambda: print(f"Exit: {crossfade_clips(args[:-1], args[-1])}") if len(args) >= 2 else print("Usage: crossfade_clips <clip1> [clip2...] <output>"),
        "generate_srt": lambda: print("generate_srt requires programmatic segment input"),
        "compose_final": lambda: print("compose_final requires programmatic input"),
    }

    handler = dispatch.get(cmd)
    if handler:
        handler()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

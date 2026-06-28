import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add bundled ffmpeg to PATH (from imageio-ffmpeg)
try:
    import imageio_ffmpeg
    _ffmpeg_dir = str(Path(imageio_ffmpeg.get_ffmpeg_exe()).parent)
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent


class Settings:
    # YouTube OAuth2
    YOUTUBE_CLIENT_ID: str = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET: str = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    YOUTUBE_REFRESH_TOKEN: str = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
    YOUTUBE_CHANNEL_ID: str = os.getenv("YOUTUBE_CHANNEL_ID", "")

    # Groq API (free tier: 30 RPM)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Pixabay API (free stock music)
    PIXABAY_API_KEY: str = os.getenv("PIXABAY_API_KEY", "")

    # Pollinations.ai (free image generation)
    POLLINATIONS_WATERMARK: str = os.getenv("POLLINATIONS_WATERMARK", "kids-video-agent")

    # Piper TTS (local, no API key needed)
    PIPER_VOICE: str = os.getenv("PIPER_VOICE", "en_US-amy-medium")

    # Content generation
    DEFAULT_TOPIC: str = os.getenv("DEFAULT_TOPIC", "learn colors")
    SCENES_PER_VIDEO: int = int(os.getenv("SCENES_PER_VIDEO", "12"))
    SCENE_DURATION: int = int(os.getenv("SCENE_DURATION", "8"))

    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    DEFAULT_CHANNEL_NAME: str = os.getenv("DEFAULT_CHANNEL_NAME", "Kids Wonderland")
    UPLOAD_SCHEDULE: str = os.getenv("UPLOAD_SCHEDULE", "weekly")

    # Email notification settings
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    NOTIFY_EMAIL: str = os.getenv("NOTIFY_EMAIL", "")

    # Output directories
    OUTPUT_DIR: Path = ROOT / "output"
    VIDEOS_DIR: Path = OUTPUT_DIR / "videos"
    AUDIO_DIR: Path = OUTPUT_DIR / "audio"
    THUMBNAILS_DIR: Path = OUTPUT_DIR / "thumbnails"
    SCRIPTS_DIR: Path = OUTPUT_DIR / "scripts"
    IMAGES_DIR: Path = OUTPUT_DIR / "images"
    MUSIC_DIR: Path = OUTPUT_DIR / "music"

    ASSETS_DIR: Path = ROOT / "src" / "assets"

    # Video settings
    FPS: int = 24
    VIDEO_RESOLUTION: tuple[int, int] = (1280, 720)

    SUPPORTED_LANGUAGES: dict[str, str] = {
        "en": "English",
        "ur": "Urdu",
        "hi": "Hindi",
    }


settings = Settings()

for d in [
    settings.OUTPUT_DIR,
    settings.VIDEOS_DIR,
    settings.AUDIO_DIR,
    settings.THUMBNAILS_DIR,
    settings.SCRIPTS_DIR,
    settings.IMAGES_DIR,
    settings.MUSIC_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

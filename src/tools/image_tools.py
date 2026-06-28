import os
import time
import requests
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"

DEFAULT_SCENE_WIDTH = 1920
DEFAULT_SCENE_HEIGHT = 1080
DEFAULT_THUMBNAIL_WIDTH = 1280
DEFAULT_THUMBNAIL_HEIGHT = 720

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
REQUEST_DELAY_SECONDS = 1.5


def _generate_url(prompt: str, width: int, height: int, seed: Optional[int] = None) -> str:
    import urllib.parse

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_BASE_URL}/{encoded_prompt}?width={width}&height={height}"
    if seed is not None:
        url += f"&seed={seed}"
    return url


def _download_image(url: str, save_path: Path, retries: int = MAX_RETRIES) -> bool:
    for attempt in range(1, retries + 1):
        try:
            logger.info("Downloading image (attempt %d/%d): %s", attempt, retries, url)
            response = requests.get(url, timeout=120, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type and not url.endswith((".png", ".jpg", ".jpeg", ".webp")):
                logger.warning("Response is not an image (Content-Type: %s)", content_type)

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = save_path.stat().st_size
            if file_size == 0:
                logger.error("Downloaded file is empty")
                save_path.unlink(missing_ok=True)
                if attempt < retries:
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue

            logger.info("Image saved to %s (%d bytes)", save_path, file_size)
            return True

        except requests.exceptions.Timeout:
            logger.warning("Request timed out (attempt %d/%d)", attempt, retries)
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error (attempt %d/%d)", attempt, retries)
        except requests.exceptions.HTTPError as e:
            logger.warning("HTTP error %s (attempt %d/%d)", e.response.status_code, attempt, retries)
        except IOError as e:
            logger.error("File write error: %s", e)
            return False

        if attempt < retries:
            delay = RETRY_DELAY_SECONDS * attempt
            logger.info("Retrying in %d seconds...", delay)
            time.sleep(delay)

    logger.error("All %d download attempts failed for URL: %s", retries, url)
    return False


def generate_scene_image(
    prompt: str,
    width: int = DEFAULT_SCENE_WIDTH,
    height: int = DEFAULT_SCENE_HEIGHT,
    seed: Optional[int] = None,
    output_path: Optional[str] = None,
) -> Optional[str]:
    if not prompt or not prompt.strip():
        logger.error("Prompt cannot be empty")
        return None

    url = _generate_url(prompt.strip(), width, height, seed)

    if output_path is None:
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prompt[:50])
        output_path = f"scene_{safe_name}_{width}x{height}.png"

    save_path = Path(output_path)
    success = _download_image(url, save_path)
    return str(save_path) if success else None


def generate_thumbnail(
    prompt: str,
    width: int = DEFAULT_THUMBNAIL_WIDTH,
    height: int = DEFAULT_THUMBNAIL_HEIGHT,
    output_path: Optional[str] = None,
) -> Optional[str]:
    if not prompt or not prompt.strip():
        logger.error("Prompt cannot be empty")
        return None

    url = _generate_url(prompt.strip(), width, height)

    if output_path is None:
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prompt[:50])
        output_path = f"thumbnail_{safe_name}.png"

    save_path = Path(output_path)
    success = _download_image(url, save_path)
    return str(save_path) if success else None


def generate_batch(
    prompts: List[str],
    output_dir: str = "output/images",
    width: int = DEFAULT_SCENE_WIDTH,
    height: int = DEFAULT_SCENE_HEIGHT,
    delay_seconds: float = REQUEST_DELAY_SECONDS,
) -> List[Optional[str]]:
    if not prompts:
        logger.warning("No prompts provided")
        return []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(prompts)

    for i, prompt in enumerate(prompts, 1):
        logger.info("Generating image %d/%d: %s", i, total, prompt[:60])

        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prompt[:50])
        filename = f"batch_{i:03d}_{safe_name}_{width}x{height}.png"
        save_path = output_path / filename

        url = _generate_url(prompt.strip(), width, height)
        success = _download_image(url, save_path)

        if success:
            results.append(str(save_path))
        else:
            logger.error("Failed to generate image %d/%d", i, total)
            results.append(None)

        if i < total:
            time.sleep(delay_seconds)

    succeeded = sum(1 for r in results if r is not None)
    logger.info("Batch complete: %d/%d images generated successfully", succeeded, total)

    return results

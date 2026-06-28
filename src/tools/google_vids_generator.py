"""Generate video clips using Google Vids/Flow.

Provides an interface for AI video generation with account-based quota management.
Browser automation via Playwright will be added later.
"""

from __future__ import annotations

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.tools import account_tracker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scene prompt templates for kids content
# ---------------------------------------------------------------------------

SCENE_PROMPTS = {
    "cinematic": (
        "A colorful animated scene of {description}, bright colors, "
        "child-friendly, 3D cartoon style, happy atmosphere"
    ),
    "educational": (
        "A fun educational scene showing {description}, vibrant colors, "
        "cute characters, safe for kids"
    ),
    "nursery": (
        "Colorful nursery rhyme scene: {description}, bright and cheerful, "
        "toddler-friendly animation"
    ),
}

# Default clip duration in seconds for Google Vids
DEFAULT_CLIP_DURATION = 8


class GoogleVidsGenerator:
    """Interface for generating video clips via Google Vids / Flow.

    Args:
        accounts_file: Path to the account quotas JSON file.
    """

    def __init__(self, accounts_file: Path | None = None) -> None:
        self._accounts_file = accounts_file or account_tracker.QUOTAS_FILE
        self._output_root = Path("output/clips")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_clip(
        self,
        prompt: str,
        account_email: str | None = None,
        style: str = "cinematic",
    ) -> Path:
        """Generate a single 8-second video clip.

        Args:
            prompt: Plain-text description of the desired clip.
            account_email: Specific account to use. If *None*, the next
                available account is chosen automatically.
            style: One of the keys in ``SCENE_PROMPTS``.

        Returns:
            Path to the downloaded ``.mp4`` file.

        Raises:
            NotImplementedError: Until browser automation is implemented.
            RuntimeError: If no accounts are available.
        """
        # 1. Resolve account
        account = self._resolve_account(account_email)
        email = account["email"]

        # 2. Build the full prompt from template
        template = SCENE_PROMPTS.get(style, SCENE_PROMPTS["cinematic"])
        full_prompt = template.format(description=prompt)

        logger.info(
            "Generating clip with account=%s style=%s prompt=%s",
            email,
            style,
            full_prompt[:80],
        )

        # TODO: Playwright automation starts here
        # Steps that will be implemented:
        #   1. Launch Chromium (headed or headless)
        #   2. Navigate to Google Vids / Flow
        #   3. Sign in with the selected account
        #   4. Paste full_prompt into the generation text box
        #   5. Select duration (8 seconds) and resolution
        #   6. Click "Generate" and wait for completion
        #   7. Extract the download URL from the result page
        raise NotImplementedError(
            "Browser automation not yet implemented. "
            "Set up Playwright and add automation code to generate_clip(). "
            f"Would generate with account: {email}, prompt: {full_prompt[:120]}"
        )

        # 8. Download clip (unreachable until automation is added)
        # output_path = self._clip_output_path(email)
        # downloaded = self.download_clip(clip_url, output_path)

        # 9. Update usage
        # account_tracker.update_usage(email, "flow_daily")
        # account_tracker.update_usage(email, "flow_monthly")

        # 10. Save metadata alongside the clip
        # self._save_metadata(downloaded, email, full_prompt, style)

        # return downloaded

    def generate_scene(
        self,
        scene_description: str,
        style: str = "cinematic",
    ) -> Path:
        """Generate a single scene suitable for a kids video.

        Args:
            scene_description: A brief description of the scene content.
            style: Prompt template style (``cinematic`` | ``educational`` |
                ``nursery``).

        Returns:
            Path to the generated clip.
        """
        return self.generate_clip(scene_description, style=style)

    def generate_video_segments(
        self,
        scenes: list[dict[str, Any]],
        output_dir: Path | None = None,
    ) -> list[Path]:
        """Generate multiple scenes and return the list of clip paths.

        Each scene dict should contain at least:
            ``description`` (str) – what the scene depicts.
        Optional keys:
            ``style`` (str) – prompt style override.

        Args:
            scenes: List of scene dicts.
            output_dir: Directory where clips are stored (overridden per-clip
                when ``None``).

        Returns:
            List of ``Path`` objects to generated clips, one per scene.

        Raises:
            NotImplementedError: Until browser automation is implemented.
        """
        results: list[Path] = []
        for idx, scene in enumerate(scenes):
            description = scene.get("description", f"scene {idx + 1}")
            style = scene.get("style", "cinematic")
            clip = self.generate_scene(description, style=style)
            results.append(clip)
        return results

    def download_clip(self, clip_url: str, output_path: Path) -> Path:
        """Download a generated clip from a URL to *output_path*.

        Args:
            clip_url: Remote URL of the clip.
            output_path: Local destination for the ``.mp4`` file.

        Returns:
            The same *output_path* after a successful download.

        Raises:
            NotImplementedError: Until browser automation is implemented.
        """
        # TODO: Implement download via requests / httpx
        # Steps:
        #   1. GET clip_url with streaming
        #   2. Write chunks to output_path
        #   3. Verify file size > 0
        raise NotImplementedError(
            "Download not yet implemented. "
            f"Would download {clip_url} -> {output_path}"
        )

    def get_status(self) -> str:
        """Return a human-readable summary of current quota usage."""
        return account_tracker.get_status_summary()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_account(self, email: str | None) -> dict[str, Any]:
        """Find or select an account with remaining quota."""
        if email:
            accounts = account_tracker.get_all_accounts()
            for acct in accounts:
                if acct["email"] == email and acct.get("is_active"):
                    return acct
            raise RuntimeError(
                f"Account {email!r} not found or inactive."
            )

        account = account_tracker.get_next_account()
        if account is None:
            raise RuntimeError(
                "No accounts with remaining quota. "
                "Add an account or wait for quota reset."
            )

        # Warn if quota is low
        if account_tracker.check_quota_low(account["email"]):
            logger.warning(
                "Quota is low for account %s — consider rotating.",
                account["email"],
            )

        return account

    def _clip_output_path(self, account_email: str) -> Path:
        """Build the output path for a new clip.

        ``output/clips/{account_name}/clip_{timestamp}.mp4``
        """
        account_name = account_email.split("@")[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._output_root / account_name / f"clip_{timestamp}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _save_metadata(
        self,
        clip_path: Path,
        account_email: str,
        prompt: str,
        style: str,
    ) -> None:
        """Write a companion metadata JSON next to the clip."""
        meta = {
            "clip_file": str(clip_path),
            "account": account_email,
            "prompt": prompt,
            "style": style,
            "duration_seconds": DEFAULT_CLIP_DURATION,
            "generated_at": datetime.now().isoformat(),
        }
        meta_path = clip_path.with_suffix(".json")
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

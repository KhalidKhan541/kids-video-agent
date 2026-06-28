import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from src.config import settings


def get_upload_schedule(schedule: str) -> datetime | None:
    schedule = schedule.lower().strip()
    now = datetime.utcnow()

    if schedule == "daily":
        return now + timedelta(days=1)
    elif schedule == "weekly":
        return now + timedelta(weeks=1)
    elif schedule == "biweekly":
        return now + timedelta(weeks=2)
    elif schedule == "monthly":
        return now + timedelta(days=30)
    elif schedule == "asap":
        return now
    else:
        try:
            days = int(schedule.replace("days", "").strip())
            return now + timedelta(days=days)
        except (ValueError, AttributeError):
            return now + timedelta(days=7)


class YouTubeUploader:
    def __init__(self):
        self.ready = bool(
            settings.YOUTUBE_CLIENT_ID
            and settings.YOUTUBE_CLIENT_SECRET
        )
        self.service = None
        if self.ready:
            self._init_service()

    def _init_service(self):
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None,
                refresh_token=settings.YOUTUBE_REFRESH_TOKEN,
                client_id=settings.YOUTUBE_CLIENT_ID,
                client_secret=settings.YOUTUBE_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
            )
            self.service = build("youtube", "v3", credentials=creds)
            self.ready = True
        except Exception as e:
            self.ready = False
            self._auth_error = str(e)

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category_id: str = "24",
        privacy_status: str = "public",
        publish_at: str = "",
        thumbnail_path: str | None = None,
    ) -> dict:
        if not self.ready or not self.service:
            return self._saved_for_manual(
                video_path, title, description, tags, category_id,
                privacy_status, publish_at, thumbnail_path,
            )

        try:
            from googleapiclient.http import MediaFileUpload

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": category_id,
                },
                "status": {
                    "privacyStatus": privacy_status,
                },
            }

            if publish_at:
                body["status"]["publishAt"] = publish_at

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = request.execute()

            video_id = response.get("id", "")

            if thumbnail_path and Path(thumbnail_path).exists() and video_id:
                try:
                    self.service.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path),
                    ).execute()
                except Exception:
                    pass

            return {
                "success": True,
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
            }

        except Exception as e:
            return self._saved_for_manual(
                video_path, title, description, tags, category_id,
                privacy_status, publish_at, thumbnail_path,
                error=str(e),
            )

    def _saved_for_manual(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category_id: str = "24",
        privacy_status: str = "public",
        publish_at: str = "",
        thumbnail_path: str | None = None,
        error: str = "",
    ) -> dict:
        manifest = {
            "video_path": video_path,
            "title": title,
            "description": description,
            "tags": tags or [],
            "category_id": category_id,
            "privacy_status": privacy_status,
            "publish_at": publish_at,
            "thumbnail_path": thumbnail_path,
            "generated_at": datetime.utcnow().isoformat(),
            "channel": settings.DEFAULT_CHANNEL_NAME,
        }

        manifest_path = settings.OUTPUT_DIR / "upload_manifest.json"
        existing = []
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text())
                if not isinstance(existing, list):
                    existing = [existing]
            except (json.JSONDecodeError, Exception):
                existing = []
        existing.append(manifest)
        manifest_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return {
            "success": False,
            "video_id": "",
            "error": error or "YouTube API not authenticated — manifest saved",
            "manifest_path": str(manifest_path),
        }

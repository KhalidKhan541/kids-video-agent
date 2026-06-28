from __future__ import annotations
from typing import TypedDict, Optional, Literal
from dataclasses import dataclass, field
from typing_extensions import NotRequired
import datetime


class ScenePlan(TypedDict):
    scene_id: int
    description: str
    narration_text: str
    duration_seconds: int
    image_prompt: NotRequired[str]
    image_path: NotRequired[str]
    audio_path: NotRequired[str]


class YouTubeMetadata(TypedDict):
    title: str
    description: str
    tags: list[str]
    category_id: str
    privacy_status: Literal["public", "unlisted", "private"]
    publish_at: NotRequired[str]
    language: str
    thumbnail_path: NotRequired[str]


class VideoProject(TypedDict):
    topic: str
    language: str
    script: str
    scenes: list[ScenePlan]
    images_dir: NotRequired[str]
    audio_dir: NotRequired[str]
    music_path: NotRequired[str]
    final_video_path: NotRequired[str]
    thumbnail_path: NotRequired[str]
    youtube_metadata: NotRequired[YouTubeMetadata]
    upload_result: NotRequired[dict]
    status: str
    error: NotRequired[str]


@dataclass
class AgentState:
    project: VideoProject
    iteration: int = 0
    logs: list[str] = field(default_factory=list)
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)

    @property
    def elapsed(self) -> str:
        delta = datetime.datetime.now() - self.start_time
        return f"{delta.seconds // 60}m {delta.seconds % 60}s"

"""Scene renderer — renders scenes using Pillow + MoviePy (no Blender)."""

from pathlib import Path
from src.config import settings
from src.agent.state import AgentState
from src.tools.scene_renderer import render_all_scenes


class BlenderRendererNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        scenes = proj.get("scenes", [])

        render_dir = settings.RENDERS_DIR / proj.get("topic", "video").replace(" ", "_")
        duration = scenes[0].get("duration_seconds", settings.SCENE_DURATION) if scenes else settings.SCENE_DURATION

        clip_paths = render_all_scenes(
            scenes=scenes,
            output_dir=render_dir,
            width=settings.VIDEO_RESOLUTION[0],
            height=settings.VIDEO_RESOLUTION[1],
            duration=duration,
            fps=settings.FPS,
        )

        updated_scenes = []
        for i, scene in enumerate(scenes):
            clip_path = clip_paths[i] if i < len(clip_paths) else None
            updated_scenes.append({
                **scene,
                "rendered_clip_path": str(clip_path) if clip_path and clip_path.exists() else "",
            })

        return {
            "project": {
                **proj,
                "scenes": updated_scenes,
                "status": "rendered",
            },
            "logs": [
                f"[Renderer] Rendered {len(clip_paths)} scene clips using Pillow",
                f"[Renderer] Output: {render_dir}",
            ],
        }

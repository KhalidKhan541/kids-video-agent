from pathlib import Path
from src.agent.state import AgentState
from src.tools.ffmpeg_tools import compose_final


class VideoComposerNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        scenes = proj.get("scenes", [])
        topic = proj.get("topic", "kids video")

        images = []
        for scene in scenes:
            img = scene.get("image_path", "")
            if img and Path(img).exists():
                images.append(img)

        if not images:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": "No scene images found to compose video",
                },
                "logs": ["[Composer] No images available"],
            }

        audio_files = [s.get("audio_path", "") for s in scenes if s.get("audio_path")]
        narration_audio = audio_files[0] if audio_files else ""

        if not narration_audio or not Path(narration_audio).exists():
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": "No narration audio found",
                },
                "logs": ["[Composer] No audio file available"],
            }

        music = proj.get("music_path", "")
        if music and not Path(music).exists():
            music = ""

        output_path = f"output/videos/{topic.replace(' ', '_').lower()}.mp4"

        try:
            rc = compose_final(
                images=images,
                audio=narration_audio,
                music=music if music else None,
                output_path=output_path,
            )

            if rc != 0:
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": f"FFmpeg exited with code {rc}",
                    },
                    "logs": [f"[Composer] FFmpeg failed with code {rc}"],
                }

            return {
                "project": {
                    **proj,
                    "final_video_path": output_path,
                    "status": "composed",
                },
                "logs": [
                    f"[Composer] Composed {len(images)} images into video",
                    f"[Composer] Output: {output_path}",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[Composer] Exception: {e}"],
            }

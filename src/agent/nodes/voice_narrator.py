from pathlib import Path
from src.agent.state import AgentState
from src.tools.piper_tts_tools import generate_narration_segments, AVAILABLE_VOICES


class VoiceNarratorNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        scenes = proj.get("scenes", [])
        language = proj.get("language", "en")
        topic = proj.get("topic", "kids video")

        if not scenes:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": "No scenes to narrate",
                },
                "logs": ["[VoiceNarrator] No scenes provided"],
            }

        segments = []
        for scene in scenes:
            text = scene.get("narration_text", "")
            if text.strip():
                segments.append({
                    "text": text,
                    "filename": f"scene_{scene.get('scene_id', 0):03d}.wav",
                })

        if not segments:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": "No narration text found in scenes",
                },
                "logs": ["[VoiceNarrator] All narration texts empty"],
            }

        voices = AVAILABLE_VOICES.get(language, AVAILABLE_VOICES.get("en", []))
        voice = voices[0] if voices else "en_US-amy-medium"

        output_dir = str(Path(proj.get("audio_dir", "")) or f"output/audio/{topic.replace(' ', '_').lower()}")

        try:
            generated = generate_narration_segments(
                segments=segments,
                output_dir=output_dir,
                voice=voice,
            )

            if not generated:
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": "All narration generations failed",
                    },
                    "logs": [f"[VoiceNarrator] All {len(segments)} generations failed"],
                }

            updated_scenes = []
            audio_map = {Path(g).name: g for g in generated}
            for scene in scenes:
                s = dict(scene)
                filename = f"scene_{s.get('scene_id', 0):03d}.wav"
                if filename in audio_map:
                    s["audio_path"] = audio_map[filename]
                updated_scenes.append(s)

            return {
                "project": {
                    **proj,
                    "scenes": updated_scenes,
                    "audio_dir": output_dir,
                    "status": "narration_done",
                },
                "logs": [
                    f"[VoiceNarrator] Generated {len(generated)}/{len(segments)} audio files",
                    f"[VoiceNarrator] Voice: {voice}",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[VoiceNarrator] Exception: {e}"],
            }

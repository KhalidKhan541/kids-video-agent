from src.agent.state import AgentState
from src.tools.groq_tools import generate_script


class ScriptWriterNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        topic = proj.get("topic", "kids video")
        language = proj.get("language", "en")

        try:
            result = generate_script(topic=topic, language=language)

            if not result.get("success"):
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": result.get("error", "Script generation failed"),
                    },
                    "logs": [f"[ScriptWriter] Error: {result.get('error')}"],
                }

            scenes = []
            for s in result.get("scenes", []):
                scenes.append({
                    "scene_id": s.get("scene_id", 0),
                    "description": s.get("description", ""),
                    "narration_text": s.get("narration", ""),
                    "image_prompt": s.get("image_prompt", ""),
                    "duration_seconds": s.get("duration_seconds", 5),
                })

            return {
                "project": {
                    **proj,
                    "script": result.get("narration_text", ""),
                    "scenes": scenes,
                    "status": "script_written",
                },
                "logs": [
                    f"[ScriptWriter] Generated {len(scenes)} scenes for '{topic}'",
                    f"[ScriptWriter] Language: {language}",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[ScriptWriter] Exception: {e}"],
            }

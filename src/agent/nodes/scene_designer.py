"""Scene designer — adds visual prompts for Pillow-based rendering."""

from src.agent.state import AgentState
from src.config import settings


class SceneDesignerNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        scenes = proj.get("scenes", [])

        for i, scene in enumerate(scenes):
            if not scene.get("image_prompt"):
                scene["image_prompt"] = self._generate_prompt(scene, i)

        return {
            "project": {
                **proj,
                "scenes": scenes,
                "status": "scenes_designed",
            },
            "logs": [
                f"[SceneDesigner] Added image prompts for {len(scenes)} scenes",
            ],
        }

    def _generate_prompt(self, scene: dict, idx: int) -> str:
        desc = scene.get("description", "")
        return f"Colorful cartoon scene for kids: {desc}"

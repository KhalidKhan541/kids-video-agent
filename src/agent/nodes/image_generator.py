from pathlib import Path
from src.agent.state import AgentState
from src.tools.image_tools import generate_batch


class ImageGeneratorNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        scenes = proj.get("scenes", [])
        topic = proj.get("topic", "kids video")

        if not scenes:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": "No scenes to generate images for",
                },
                "logs": ["[ImageGen] No scenes provided"],
            }

        prompts = [s.get("image_prompt", s.get("description", "")) for s in scenes]
        prompts = [p for p in prompts if p.strip()]

        if not prompts:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": "No image prompts found in scenes",
                },
                "logs": ["[ImageGen] All prompts empty"],
            }

        output_dir = str(Path(proj.get("images_dir", "")) or f"output/images/{topic.replace(' ', '_').lower()}")

        try:
            results = generate_batch(
                prompts=prompts,
                output_dir=output_dir,
            )

            succeeded = [r for r in results if r is not None]
            failed = len(prompts) - len(succeeded)

            updated_scenes = []
            for i, scene in enumerate(scenes):
                s = dict(scene)
                if i < len(results) and results[i]:
                    s["image_path"] = results[i]
                updated_scenes.append(s)

            if not succeeded:
                return {
                    "project": {
                        **proj,
                        "scenes": updated_scenes,
                        "status": "error",
                        "error": f"All {len(prompts)} image generations failed",
                    },
                    "logs": [f"[ImageGen] All {len(prompts)} generations failed"],
                }

            status = "images_generated" if failed == 0 else "images_partial"
            return {
                "project": {
                    **proj,
                    "scenes": updated_scenes,
                    "images_dir": output_dir,
                    "status": status,
                },
                "logs": [
                    f"[ImageGen] Generated {len(succeeded)}/{len(prompts)} images",
                    f"[ImageGen] Saved to {output_dir}",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[ImageGen] Exception: {e}"],
            }

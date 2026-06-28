"""Content planner — generates video content for any topic using Ollama."""

from src.config import settings
from src.agent.state import AgentState
from src.tools.content_generator import generate_content


class ContentPlannerNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        topic = proj.get("topic", settings.DEFAULT_TOPIC)

        try:
            content = generate_content(topic)
        except Exception as e:
            content = {
                "title": f"Fun Video About {topic}",
                "topic": topic,
                "age_group": "2-4 years",
                "description": f"A fun kids video about {topic}",
                "scenes": [
                    {"scene_id": i + 1, "description": f"Scene about {topic}",
                     "narration": f"Let's learn about {topic}!",
                     "image_prompt": f"Colorful cartoon scene about {topic}",
                     "duration_seconds": 8}
                    for i in range(settings.SCENES_PER_VIDEO)
                ],
                "tags": [topic, "kids", "learning", "fun"],
                "fun_fact": "",
            }

        scenes = content.get("scenes", [])

        return {
            "project": {
                **proj,
                "topic": content.get("topic", topic),
                "script": content.get("description", ""),
                "scenes": scenes,
                "youtube_metadata": {
                    "title": content.get("title", f"Kids Video: {topic}"),
                    "description": content.get("description", ""),
                    "tags": content.get("tags", []),
                    "category_id": "24",
                    "privacy_status": "public",
                    "language": proj.get("language", "en"),
                },
                "status": "content_planned",
            },
            "logs": [
                f"[Planner] Generated content for topic: {topic}",
                f"[Planner] Title: {content.get('title', 'N/A')[:60]}",
                f"[Planner] Scenes: {len(scenes)}",
                f"[Planner] Tags: {len(content.get('tags', []))}",
            ],
        }

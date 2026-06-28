"""Agent 1: PromptAgent - Generates scene descriptions + Bing Image Creator prompts."""

import re
from typing import Any

from src.tools.groq_tools import generate_script


def run(topic: str, num_scenes: int = 12, language: str = "en", **kwargs) -> dict[str, Any]:
    result = generate_script(topic, language=language)

    if not result.get("success"):
        return {
            "agent": "PromptAgent",
            "topic": topic,
            "slug": re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_"),
            "num_scenes": 0,
            "scenes": [],
            "narration_text": "",
            "error": result.get("error", "Unknown error"),
        }

    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    scenes = result.get("scenes", [])

    return {
        "agent": "PromptAgent",
        "topic": topic,
        "title": topic.title(),
        "slug": slug,
        "num_scenes": len(scenes),
        "scenes": scenes,
        "narration_text": result.get("narration_text", ""),
    }

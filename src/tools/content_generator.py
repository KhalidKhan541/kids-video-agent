"""AI-powered content generator using Ollama for any kids video topic."""

import json
import re
from typing import Optional

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import settings


SYSTEM_PROMPT = """Generate a kids video JSON for topic: {topic}

JSON only, no markdown:
{{"title":"title with emoji","scenes":[{{"scene_id":1,"narration":"short sentence","description":"visual"}}],"tags":["tag1","tag2","tag3","tag4","tag5"]}}

Rules: 4 scenes, each narration under 10 words, simple English, tags for YouTube SEO."""


def _build_chain() -> any:
    """Build the Ollama generation chain."""
    llm = OllamaLLM(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.8,
        num_predict=500,
    )

    prompt = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=["topic"],
    )

    return prompt | llm | StrOutputParser()


def generate_content(topic: str) -> dict:
    """Generate complete video content for any topic using Ollama.

    Args:
        topic: The video topic (e.g., "learn colors", "animal sounds")

    Returns:
        dict with keys: title, topic, age_group, description, scenes, tags, fun_fact
    """
    chain = _build_chain()
    raw = chain.invoke({"topic": topic})

    # Clean up: remove markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse Ollama output as JSON:\n{raw[:500]}")

    # Validate required fields
    required = ["title", "scenes", "tags"]
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Ensure scenes have required structure
    for i, scene in enumerate(data["scenes"]):
        scene.setdefault("scene_id", i + 1)
        scene.setdefault("duration_seconds", 5)
        scene.setdefault("narration", "")
        scene.setdefault("description", f"Scene {i + 1}")
        scene.setdefault("image_prompt", scene["description"])

    # Set defaults
    data.setdefault("topic", topic)
    data.setdefault("age_group", "2-4 years")
    data.setdefault("description", f"A fun kids video about {topic}")
    data.setdefault("fun_fact", "")

    return data


def generate_title(topic: str, lang: str = "en") -> str:
    """Generate just a title for the topic."""
    llm = OllamaLLM(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.9,
        num_predict=100,
    )
    result = llm.invoke(
        f"Generate a catchy YouTube Kids video title about '{topic}'. "
        f"Include 1 emoji. Only output the title, nothing else."
    )
    return result.strip().strip('"').strip("'")


def generate_tags(topic: str) -> list[str]:
    """Generate YouTube SEO tags for the topic."""
    llm = OllamaLLM(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.5,
        num_predict=200,
    )
    result = llm.invoke(
        f"Generate 10 YouTube SEO tags for a kids video about '{topic}'. "
        f"Output as comma-separated list, no quotes, no numbering."
    )
    tags = [t.strip() for t in result.split(",") if t.strip()]
    return tags[:10]

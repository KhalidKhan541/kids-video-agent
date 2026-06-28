"""Groq API tools for kids video content generation using Llama 3."""

import json
import logging
import os
from typing import Any

from groq import Groq

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    """Get or create a Groq client singleton."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


def _chat_completion(prompt: str, max_tokens: int = 4096) -> str:
    """Send a chat completion request to Groq."""
    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


def _parse_json(text: str) -> dict[str, Any]:
    """Extract and parse JSON from a model response, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def generate_script(topic: str, language: str = "en", num_scenes: int = 40) -> dict[str, Any]:
    """Generate a kids video script with scenes, narration, and image prompts.

    Args:
        topic: The video topic (e.g. "animal sounds", "learn colors").
        language: ISO 639-1 language code. Defaults to "en".
        num_scenes: Number of scenes to generate. Defaults to 40.

    Returns:
        Structured dict with topic, language, scenes, and narration_text.
    """
    lang_names = {
        "en": "English", "es": "Spanish", "fr": "French",
        "de": "German", "pt": "Portuguese", "hi": "Hindi",
        "ar": "Arabic", "ja": "Japanese", "zh": "Chinese",
    }
    lang_label = lang_names.get(language, language)

    prompt = f"""You are a creative writer for kids educational videos.
Write a complete script about "{topic}" in {lang_label}.

Return ONLY valid JSON (no markdown, no commentary) with this exact structure:
{{
  "topic": "{topic}",
  "language": "{language}",
  "num_scenes": {num_scenes},
  "scenes": [
    {{
      "scene_id": 1,
      "description": "A short visual description of what appears on screen",
      "narration": "The spoken narration text for this scene",
      "image_prompt": "A detailed image generation prompt for this scene, Pixar-style 3D cartoon, bright colors, kid-friendly"
    }}
  ],
  "narration_text": "Full narration text concatenated into a single paragraph"
}}

Rules:
- Create exactly {num_scenes} scenes
- Each scene should flow naturally to the next with proper storytelling
- Narration must be simple, short sentences suitable for children ages 2-6
- Image prompts must be descriptive and end with "Pixar style 3D cartoon, bright vivid colors, child-friendly, no text, clean background"
- All text must be in {lang_label}
- Keep each narration line under 15 words
- Create a complete story arc with beginning, middle, and end
- Use repetition and rhythm to make it engaging for toddlers"""

    try:
        raw = _chat_completion(prompt)
        data = _parse_json(raw)
        logger.info("Generated script for topic=%s lang=%s", topic, language)
        return {
            "success": True,
            "agent": "groq_llama3",
            "topic": data.get("topic", topic),
            "language": data.get("language", language),
            "num_scenes": data.get("num_scenes", len(data.get("scenes", []))),
            "scenes": data.get("scenes", []),
            "narration_text": data.get("narration_text", ""),
        }
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from Groq response: %s", exc)
        return {"success": False, "error": f"JSON parse error: {exc}"}
    except Exception as exc:
        logger.error("Groq API error in generate_script: %s", exc)
        return {"success": False, "error": str(exc)}


def generate_seo(title: str) -> dict[str, Any]:
    """Generate YouTube SEO metadata for a kids video.

    Args:
        title: The video title or topic.

    Returns:
        Dict with optimized title, description, and tags.
    """
    prompt = f"""You are a YouTube SEO expert specializing in kids educational content.
Generate optimized SEO metadata for a YouTube kids video titled: "{title}"

Return ONLY valid JSON (no markdown, no commentary) with this exact structure:
{{
  "title": "An optimized YouTube title (max 60 chars, catchy, includes main keyword)",
  "description": "A 2-3 sentence YouTube description (max 200 chars) that is engaging and keyword-rich",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"]
}}

Rules:
- Title must be under 60 characters, start with a capital letter, and be click-worthy
- Description should encourage parents to watch and subscribe
- Provide exactly 10 relevant tags mixing broad and specific keywords
- Tags should include: topic, age group ("kids", "toddlers", "babies"), format ("nursery rhyme", "learning video", "educational"), and related concepts"""

    try:
        raw = _chat_completion(prompt)
        data = _parse_json(raw)
        logger.info("Generated SEO for title=%s", title)
        return {
            "success": True,
            "agent": "groq_llama3",
            "title": data.get("title", title),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
        }
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from Groq response: %s", exc)
        return {"success": False, "error": f"JSON parse error: {exc}"}
    except Exception as exc:
        logger.error("Groq API error in generate_seo: %s", exc)
        return {"success": False, "error": str(exc)}


def generate_thumbnails_prompt(topic: str) -> dict[str, Any]:
    """Generate image prompts for YouTube thumbnail variations.

    Args:
        topic: The video topic.

    Returns:
        Dict with a list of thumbnail prompt variations.
    """
    prompt = f"""You are a thumbnail designer for kids YouTube channels.
Generate 3 different thumbnail image prompts for a video about "{topic}".

Return ONLY valid JSON (no markdown, no commentary) with this exact structure:
{{
  "topic": "{topic}",
  "thumbnails": [
    {{
      "variant": "A",
      "prompt": "A detailed image generation prompt for thumbnail variant A"
    }},
    {{
      "variant": "B",
      "prompt": "A detailed image generation prompt for thumbnail variant B"
    }},
    {{
      "variant": "C",
      "prompt": "A detailed image generation prompt for thumbnail variant C"
    }}
  ]
}}

Rules:
- Each prompt must describe a single striking image (no text in the image)
- Use vibrant, saturated colors that pop at small sizes
- Include expressive characters or objects that convey excitement
- Style: Pixar 3D cartoon, bright vivid colors, child-friendly
- Prompts must be specific and descriptive (50-80 words each)
- End each prompt with "YouTube thumbnail style, high contrast, eye-catching" """

    try:
        raw = _chat_completion(prompt)
        data = _parse_json(raw)
        logger.info("Generated thumbnail prompts for topic=%s", topic)
        return {
            "success": True,
            "agent": "groq_llama3",
            "topic": data.get("topic", topic),
            "thumbnails": data.get("thumbnails", []),
        }
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from Groq response: %s", exc)
        return {"success": False, "error": f"JSON parse error: {exc}"}
    except Exception as exc:
        logger.error("Groq API error in generate_thumbnails_prompt: %s", exc)
        return {"success": False, "error": str(exc)}

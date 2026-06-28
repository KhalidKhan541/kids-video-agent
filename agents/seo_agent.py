from src.tools.groq_tools import generate_seo_metadata


def run(topic: str, scenes=None, **kwargs) -> dict:
    result = generate_seo_metadata(topic, scenes)
    
    return {
        "agent": "SEOAgent",
        "topic": topic,
        "title": result.get("title", topic),
        "description": result.get("description", ""),
        "tags": result.get("tags", []),
        "category_id": result.get("category_id", ""),
        "thumbnail_suggestion": result.get("thumbnail_suggestion", ""),
    }

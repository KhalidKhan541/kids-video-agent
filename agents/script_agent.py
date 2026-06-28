"""ScriptWriter Agent - Generates video scripts using Groq API (Llama 3)."""

from pathlib import Path
from typing import Any


def run(topic: str, num_scenes: int = 12, language: str = "en", **kwargs) -> dict[str, Any]:
    try:
        from src.tools.groq_tools import generate_script
        result = generate_script(topic, language=language)
        result["agent"] = "ScriptWriter"
        return result
    except Exception as e:
        return {"agent": "ScriptWriter", "error": str(e), "scenes": []}

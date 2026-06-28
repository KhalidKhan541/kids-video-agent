import json
from pathlib import Path
from typing import Optional
from src.config import settings


class AssetRegistry:
    def __init__(self):
        self.index_path = settings.ASSETS_DIR / "registry.json"
        self._assets = self._load()

    def _load(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, Exception):
                pass
        return {"characters": [], "backgrounds": [], "music": [], "props": []}

    def _save(self):
        self.index_path.write_text(json.dumps(self._assets, indent=2), encoding="utf-8")

    def register(self, category: str, name: str, path: str, tags: list[str] | None = None):
        if category not in self._assets:
            self._assets[category] = []
        entry = {"name": name, "path": path, "tags": tags or []}
        self._assets[category] = [
            a for a in self._assets[category] if a["name"] != name
        ]
        self._assets[category].append(entry)
        self._save()

    def get(self, category: str, name: str) -> Optional[dict]:
        for a in self._assets.get(category, []):
            if a["name"] == name:
                return a
        return None

    def search(self, category: str, query: str) -> list[dict]:
        q = query.lower()
        return [
            a for a in self._assets.get(category, [])
            if q in a["name"].lower() or any(q in t.lower() for t in a.get("tags", []))
        ]

    def list_category(self, category: str) -> list[str]:
        return [a["name"] for a in self._assets.get(category, [])]

    def suggest_for_rhyme(self, rhyme_name: str) -> dict:
        rhyme_lower = rhyme_name.lower()
        suggestions = {"characters": [], "backgrounds": [], "music": []}

        keyword_map = {
            "star": ("characters", "star"),
            "farm": ("backgrounds", "farm"),
            "animal": ("characters", "animal"),
            "boat": ("backgrounds", "water"),
            "bus": ("characters", "vehicle"),
            "lamb": ("characters", "animal"),
            "nature": ("backgrounds", "nature"),
        }

        for keyword, (cat, tag) in keyword_map.items():
            if keyword in rhyme_lower:
                suggestions[cat] = self.search(cat, tag)

        return suggestions


asset_registry = AssetRegistry()

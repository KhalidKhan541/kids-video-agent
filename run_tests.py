"""Quick inline tests for Kids Video Agent core."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agent.state import AgentState
from src.agent.graph import create_initial_project
from src.templates.rhymes import RHYME_TEMPLATES, get_rhyme_names, search_rhymes
from src.config import settings

passed = 0

p = create_initial_project()
assert p["status"] == "planned"
assert p["blender_config"]["scene_type"] == "simple"
passed += 1; print("PASS create_initial_project")

assert "Twinkle Twinkle Little Star" in RHYME_TEMPLATES
assert len(RHYME_TEMPLATES) >= 6
passed += 1; print(f"PASS {len(RHYME_TEMPLATES)} rhyme templates")

for name, data in RHYME_TEMPLATES.items():
    assert "lyrics" in data, f"{name} missing lyrics"
    assert "en" in data["lyrics"], f"{name} missing en"
passed += 1; print("PASS all rhymes have English lyrics")

r = search_rhymes("star")
assert len(r) > 0
passed += 1; print(f"PASS search_rhymes -> {len(r)} results")

s = AgentState(project=p)
assert s.iteration == 0
assert s.logs == []
passed += 1; print("PASS AgentState creation")

bc = p["blender_config"]
assert bc["resolution"] == (1920, 1080)
assert bc["fps"] == 24
assert bc["background_music"] == True
passed += 1; print("PASS BlenderConfig defaults")

assert "en" in settings.SUPPORTED_LANGUAGES
assert "hi" in settings.SUPPORTED_LANGUAGES
assert len(settings.SUPPORTED_LANGUAGES) >= 4
passed += 1; print(f"PASS {len(settings.SUPPORTED_LANGUAGES)} languages")

has_hindi = any("hi" in data.get("lyrics", {}) for data in RHYME_TEMPLATES.values())
assert has_hindi
passed += 1; print("PASS at least one rhyme has Hindi lyrics")

names = get_rhyme_names()
assert len(names) == len(RHYME_TEMPLATES)
passed += 1; print(f"PASS get_rhyme_names -> {len(names)} names")

print(f"\nAll {passed} tests passed!")

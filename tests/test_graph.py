"""Basic tests for the Kids Video Agent pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.state import AgentState, VideoProject
from src.agent.graph import create_initial_project
from src.templates.rhymes import RHYME_TEMPLATES, get_rhyme_names, search_rhymes


def test_create_initial_project():
    proj = create_initial_project(topic="Twinkle Twinkle Little Star", language="en")
    assert proj["topic"] == "Twinkle Twinkle Little Star"
    assert proj["language"] == "en"
    assert proj["status"] == "planned"
    assert "blender_config" in proj
    assert proj["blender_config"]["scene_type"] == "simple"


def test_create_initial_project_with_topic():
    proj = create_initial_project(topic="learn colors", language="en")
    assert proj["topic"] == "learn colors"
    assert proj["language"] == "en"
    assert proj["status"] == "planned"
    assert "blender_config" in proj


def test_create_initial_project_defaults():
    proj = create_initial_project()
    assert proj["topic"] == "learn colors"
    assert proj["language"] == "en"


def test_rhyme_templates_exist():
    assert len(RHYME_TEMPLATES) > 0
    assert "Twinkle Twinkle Little Star" in RHYME_TEMPLATES
    assert "Old MacDonald Had a Farm" in RHYME_TEMPLATES


def test_rhyme_has_lyrics():
    for name, data in RHYME_TEMPLATES.items():
        assert "lyrics" in data, f"{name} missing lyrics"
        assert "en" in data["lyrics"], f"{name} missing English lyrics"
        assert len(data["lyrics"]["en"]) > 0, f"{name} has empty lyrics"


def test_get_rhyme_names():
    names = get_rhyme_names()
    assert len(names) == len(RHYME_TEMPLATES)
    assert all(n in RHYME_TEMPLATES for n in names)


def test_search_rhymes():
    results = search_rhymes("star")
    assert len(results) > 0
    assert any("Twinkle" in r[0] for r in results)

    results_farm = search_rhymes("farm")
    assert any("MacDonald" in r[0] for r in results_farm)


def test_agent_state_creation():
    proj = create_initial_project()
    state = AgentState(project=proj)
    assert state.project["status"] == "planned"
    assert state.iteration == 0
    assert state.logs == []


def test_supported_languages():
    from src.config import settings
    assert "en" in settings.SUPPORTED_LANGUAGES
    assert "ur" in settings.SUPPORTED_LANGUAGES
    assert "hi" in settings.SUPPORTED_LANGUAGES


def test_blender_config_defaults():
    proj = create_initial_project()
    bc = proj["blender_config"]
    assert bc["resolution"] == (1920, 1080)
    assert bc["fps"] == 24
    assert bc["duration_seconds"] == 180
    assert bc["background_music"] is True

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.agent.state import AgentState, VideoProject
from src.tools.groq_tools import generate_script, generate_seo
from src.tools.image_tools import generate_batch
from src.tools.piper_tts_tools import generate_narration
from src.tools.music_tools import get_kids_bgm
from src.tools.ffmpeg_tools import compose_final
import os
from pathlib import Path


def script_writer(state: AgentState) -> dict:
    project = state.project
    result = generate_script(project["topic"], project["language"])
    if not result.get("success"):
        return {"project": {**project, "status": "failed", "error": result.get("error", "Script generation failed")}}
    scenes = []
    for s in result.get("scenes", []):
        scenes.append({
            "scene_id": s.get("scene_id", 0),
            "description": s.get("description", ""),
            "narration_text": s.get("narration", ""),
            "duration_seconds": 5,
            "image_prompt": s.get("image_prompt", ""),
        })
    return {"project": {**project, "script": result.get("narration_text", ""), "scenes": scenes, "status": "scripted"}}


def image_generator(state: AgentState) -> dict:
    project = state.project
    scenes = project.get("scenes", [])
    if not scenes:
        return {"project": {**project, "status": "failed", "error": "No scenes to generate images for"}}
    output_dir = f"output/{project['topic'].replace(' ', '_')}/images"
    prompts = [s.get("image_prompt", "") for s in scenes]
    paths = generate_batch(prompts, output_dir=output_dir)
    updated_scenes = []
    for i, scene in enumerate(scenes):
        path = paths[i] if i < len(paths) else None
        updated_scenes.append({**scene, "image_path": path or ""})
    return {"project": {**project, "scenes": updated_scenes, "images_dir": output_dir, "status": "images_done"}}


def voice_narrator(state: AgentState) -> dict:
    project = state.project
    scenes = project.get("scenes", [])
    if not scenes:
        return {"project": {**project, "status": "failed", "error": "No scenes for narration"}}
    output_dir = f"output/{project['topic'].replace(' ', '_')}/audio"
    os.makedirs(output_dir, exist_ok=True)
    updated_scenes = []
    for scene in scenes:
        narration_text = scene.get("narration_text", "")
        if not narration_text.strip():
            updated_scenes.append({**scene, "audio_path": ""})
            continue
        filename = f"scene_{scene['scene_id']:03d}.wav"
        output_path = os.path.join(output_dir, filename)
        try:
            generate_narration(narration_text, output_path)
            updated_scenes.append({**scene, "audio_path": output_path})
        except Exception:
            updated_scenes.append({**scene, "audio_path": ""})
    return {"project": {**project, "scenes": updated_scenes, "audio_dir": output_dir, "status": "voice_done"}}


def music_agent(state: AgentState) -> dict:
    project = state.project
    output_dir = f"output/{project['topic'].replace(' ', '_')}/music"
    os.makedirs(output_dir, exist_ok=True)
    music_path = get_kids_bgm(Path(output_dir))
    if music_path:
        return {"project": {**project, "music_path": str(music_path), "status": "music_done"}}
    return {"project": {**project, "music_path": "", "status": "music_done"}}


def video_composer(state: AgentState) -> dict:
    project = state.project
    scenes = project.get("scenes", [])
    images = [s.get("image_path", "") for s in scenes if s.get("image_path")]
    if not images:
        return {"project": {**project, "status": "failed", "error": "No images for video composition"}}
    audio_parts = [s.get("audio_path", "") for s in scenes if s.get("audio_path")]
    audio_dir = project.get("audio_dir", "")
    narration_files = sorted([os.path.join(audio_dir, f) for f in os.listdir(audio_dir) if f.endswith(".wav")]) if audio_dir and os.path.isdir(audio_dir) else audio_parts
    if not narration_files:
        return {"project": {**project, "status": "failed", "error": "No audio files for video composition"}}
    temp_narration = os.path.join(audio_dir or "output", "full_narration.wav")
    if len(narration_files) == 1:
        import shutil
        shutil.copy2(narration_files[0], temp_narration)
    else:
        from pydub import AudioSegment
        combined = AudioSegment.empty()
        for nf in narration_files:
            if os.path.exists(nf):
                combined += AudioSegment.from_wav(nf)
        combined.export(temp_narration, format="wav")
    output_dir = f"output/{project['topic'].replace(' ', '_')}"
    final_video = os.path.join(output_dir, "final_video.mp4")
    music_path = project.get("music_path", "")
    rc = compose_final(
        images=images,
        audio=temp_narration,
        music=music_path if music_path and os.path.exists(music_path) else None,
        output_path=final_video,
    )
    if rc == 0:
        return {"project": {**project, "final_video_path": final_video, "status": "composed"}}
    return {"project": {**project, "status": "failed", "error": f"FFmpeg compose failed with code {rc}"}}


def seo_optimizer(state: AgentState) -> dict:
    project = state.project
    topic = project.get("topic", "")
    result = generate_seo(topic)
    if not result.get("success"):
        return {"project": {**project, "status": "seo_done"}}
    metadata = {
        "title": result.get("title", topic),
        "description": result.get("description", ""),
        "tags": result.get("tags", []),
        "category_id": "22",
        "privacy_status": "public",
        "language": project.get("language", "en"),
    }
    return {"project": {**project, "youtube_metadata": metadata, "status": "seo_done"}}


def youtube_publisher(state: AgentState) -> dict:
    project = state.project
    return {"project": {**project, "status": "ready_to_upload"}}


def build_agent() -> StateGraph:
    workflow = StateGraph(AgentState)
    workflow.add_node("script_writer", script_writer)
    workflow.add_node("image_generator", image_generator)
    workflow.add_node("voice_narrator", voice_narrator)
    workflow.add_node("music_agent", music_agent)
    workflow.add_node("video_composer", video_composer)
    workflow.add_node("seo_optimizer", seo_optimizer)
    workflow.add_node("youtube_publisher", youtube_publisher)
    workflow.set_entry_point("script_writer")
    workflow.add_edge("script_writer", "image_generator")
    workflow.add_edge("image_generator", "voice_narrator")
    workflow.add_edge("voice_narrator", "music_agent")
    workflow.add_edge("music_agent", "video_composer")
    workflow.add_edge("video_composer", "seo_optimizer")
    workflow.add_edge("seo_optimizer", "youtube_publisher")
    workflow.add_edge("youtube_publisher", END)
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


def create_initial_project(topic: str = "learn colors", language: str = "en") -> VideoProject:
    return {
        "topic": topic,
        "language": language,
        "script": "",
        "scenes": [],
        "status": "planned",
    }


agent = build_agent()

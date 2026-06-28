from typing import TypedDict, Optional


class AgentState(TypedDict):
    project: dict
    upload: bool


def has_images(state: AgentState) -> str:
    project = state.get("project", {})
    if "images_dir" in project and project["images_dir"]:
        return "yes"
    return "no"


def has_audio(state: AgentState) -> str:
    project = state.get("project", {})
    if "audio_dir" in project and project["audio_dir"]:
        return "yes"
    return "no"


def has_video(state: AgentState) -> str:
    project = state.get("project", {})
    if "final_video_path" in project and project["final_video_path"]:
        return "yes"
    return "no"


def needs_upload(state: AgentState) -> str:
    if state.get("upload", False):
        return "upload"
    return "skip_upload"


def render_quality_gate(state: AgentState) -> str:
    project = state.get("project", {})
    if "final_video_path" in project and project["final_video_path"]:
        return "pass"
    return "retry"

from src.agent.state import AgentState


class YouTubePublisherNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project

        try:
            video_path = proj.get("final_video_path", "")
            metadata = proj.get("youtube_metadata", {})

            if not video_path:
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": "No video file to publish",
                    },
                    "logs": ["[YouTube] No video file path"],
                }

            return {
                "project": {
                    **proj,
                    "upload_result": {
                        "status": "pending",
                        "video_path": video_path,
                        "metadata": metadata,
                    },
                    "status": "ready_to_publish",
                },
                "logs": [
                    f"[YouTube] Video ready: {video_path}",
                    f"[YouTube] Title: {metadata.get('title', 'N/A')}",
                    "[YouTube] Awaiting manual upload or API credentials",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[YouTube] Exception: {e}"],
            }

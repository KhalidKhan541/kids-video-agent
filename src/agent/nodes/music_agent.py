from pathlib import Path
from src.agent.state import AgentState
from src.tools.music_tools import search_music, download_music


class MusicAgentNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        topic = proj.get("topic", "kids video")

        try:
            results = search_music(
                query=f"kids {topic} cartoon",
                category="kids",
                limit=5,
            )

            if not results:
                results = search_music(
                    query="happy children instrumental",
                    category="kids",
                    limit=5,
                )

            if not results:
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": "No music tracks found",
                    },
                    "logs": ["[Music] No tracks found for any query"],
                }

            best = max(results, key=lambda x: x.get("downloads", 0))
            output_dir = Path(f"output/music/{topic.replace(' ', '_').lower()}")
            output_path = output_dir / f"bgm_{best['id']}.mp3"

            downloaded = download_music(
                url=best["url"],
                output_path=output_path,
            )

            if not downloaded:
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": "Music download failed",
                    },
                    "logs": [f"[Music] Download failed for track {best.get('id')}"],
                }

            return {
                "project": {
                    **proj,
                    "music_path": str(downloaded),
                    "status": "music_ready",
                },
                "logs": [
                    f"[Music] Found {len(results)} tracks",
                    f"[Music] Selected: {best.get('title', 'unknown')}",
                    f"[Music] Saved to {downloaded}",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[Music] Exception: {e}"],
            }

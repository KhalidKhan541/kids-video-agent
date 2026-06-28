from src.agent.state import AgentState
from src.tools.groq_tools import generate_seo


class SEOOptimizerNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        topic = proj.get("topic", "kids video")
        title = proj.get("youtube_metadata", {}).get("title", topic)

        try:
            result = generate_seo(title=title)

            if not result.get("success"):
                return {
                    "project": {
                        **proj,
                        "status": "error",
                        "error": result.get("error", "SEO generation failed"),
                    },
                    "logs": [f"[SEO] Error: {result.get('error')}"],
                }

            existing_meta = proj.get("youtube_metadata", {})
            existing_meta.update({
                "title": result.get("title", title),
                "description": result.get("description", ""),
                "tags": result.get("tags", []),
            })

            return {
                "project": {
                    **proj,
                    "youtube_metadata": existing_meta,
                    "status": "seo_optimized",
                },
                "logs": [
                    f"[SEO] Title: {result.get('title', '')[:60]}",
                    f"[SEO] Tags: {len(result.get('tags', []))} keywords",
                ],
            }
        except Exception as e:
            return {
                "project": {
                    **proj,
                    "status": "error",
                    "error": str(e),
                },
                "logs": [f"[SEO] Exception: {e}"],
            }

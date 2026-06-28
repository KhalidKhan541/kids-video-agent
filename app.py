import streamlit as st
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

st.set_page_config(page_title="Kids Video Agent", page_icon="🎬", layout="wide")

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agent.state import AgentState
from src.agent.graph import agent, create_initial_project
from src.templates.rhymes import RHYME_TEMPLATES, get_rhyme_names, search_rhymes
from src.config import settings
from src.tools.youtube_tools import YouTubeUploader

PAGES = ["Dashboard", "Create Video", "Batch Mode", "Upload Queue", "Rhymes", "Settings"]
ICONS = ["📊", "🎬", "📦", "📤", "📖", "⚙️"]


def init_state():
    for k in ["page", "logs", "status", "history", "batch_results"]:
        if k not in st.session_state:
            defaults = {
                "page": "Dashboard", "logs": [], "status": "idle",
                "history": [], "batch_results": [],
            }
            st.session_state[k] = defaults[k]


init_state()

# ─── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🎬 Kids Video Agent")
    st.divider()

    for i, (icon, label) in enumerate(zip(ICONS, PAGES)):
        if st.button(f"{icon} {label}", use_container_width=True,
                     key=f"nav_{i}",
                     type="primary" if st.session_state.page == label else "secondary"):
            st.session_state.page = label
            st.rerun()

    st.divider()

    status_map = {"idle": "🟢 Idle", "running": "🟡 Running",
                  "done": "✅ Done", "error": "🔴 Error"}
    st.markdown(f"**Status:** {status_map.get(st.session_state.status, '⚪')}")

    vid_count = len(list(settings.VIDEOS_DIR.glob("*.mp4")))
    img_count = len(list(settings.THUMBNAILS_DIR.glob("*")))
    st.markdown(f"**Videos:** {vid_count}  |  **Thumbnails:** {img_count}")

    st.divider()
    st.caption(f"v0.1.0 · {settings.DEFAULT_CHANNEL_NAME}")


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def count_videos():
    return len(list(settings.VIDEOS_DIR.glob("*.mp4")))

def queue_count():
    p = settings.OUTPUT_DIR / "upload_manifest.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            return len(d) if isinstance(d, list) else 1
        except Exception:
            pass
    return 0


# ─── Dashboard ───────────────────────────────────────────────────────────────────

def show_dashboard():
    st.title("📊 Dashboard")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎥 Videos", count_videos())
    col2.metric("📖 Rhymes", len(get_rhyme_names()))
    col3.metric("📤 Queue", queue_count())
    col4.metric("🌐 Languages", len(settings.SUPPORTED_LANGUAGES))

    st.divider()

    left, right = st.columns([3, 2])

    with left:
        st.subheader("🚀 Quick Create")
        with st.form("quick_form", clear_on_submit=False):
            topic = st.text_input("Topic", value="learn colors", placeholder="e.g., animal sounds, colors, space")
            c1, c2 = st.columns(2)
            with c1:
                rhyme = st.selectbox("Or select a rhyme", [""] + get_rhyme_names())
            with c2:
                lang = st.selectbox("Language",
                    list(settings.SUPPORTED_LANGUAGES.items()),
                    format_func=lambda x: f"{x[1]} ({x[0]})")
            style = st.select_slider("Animation style",
                options=["simple", "character", "nature", "abstract"],
                value="character")

            if st.form_submit_button("🚀 Generate Video", use_container_width=True):
                run_pipeline(topic=topic or rhyme, language=lang[0], scene_type=style)

        if st.session_state.logs:
            with st.expander("Recent logs", expanded=False):
                for log in st.session_state.logs[-8:]:
                    st.code(log)

    with right:
        st.subheader("📈 Recent")
        if st.session_state.history:
            for item in st.session_state.history[-6:][::-1]:
                c = {"completed": "green", "error": "red", "running": "orange"}
                st.markdown(
                    f":{c.get(item['status'],'gray')}[**{item['rhyme'][:30]}**]  "
                    f"`{item['time']}`  ·  {item['status']}"
                )
        else:
            st.info("No videos yet.")

    st.divider()
    st.subheader("💡 Quick Picks")
    cols = st.columns(5)
    picks = [
        ("learn colors", "🎨"),
        ("animal sounds", "🐄"),
        ("the solar system", "🌍"),
        ("good manners", "😊"),
        ("counting 1-10", "🔢"),
    ]
    for i, (name, emoji) in enumerate(picks):
        with cols[i]:
            if st.button(f"{emoji} {name[:14]}...", use_container_width=True):
                st.session_state.page = "Create Video"
                st.session_state.selected_topic = name
                st.rerun()


# ─── Create Video ────────────────────────────────────────────────────────────────

def show_create():
    st.title("🎬 Create Video")

    steps_labels = ["Plan", "Script", "Scenes", "Render", "Audio",
                    "Compose", "Thumbnail", "SEO", "Publish"]

    form_col, progress_col = st.columns([1, 1])

    with form_col:
        st.subheader("Video Details")
        with st.form("create_form", clear_on_submit=False):
            topic = st.text_input("Topic",
                value=getattr(st.session_state, 'selected_topic', 'learn colors'),
                placeholder="e.g., animal sounds, colors, space")

            all_rhymes = get_rhyme_names()

            rhyme = st.selectbox("Or select a nursery rhyme", [""] + all_rhymes)

            lang = st.selectbox("Language",
                list(settings.SUPPORTED_LANGUAGES.items()),
                format_func=lambda x: f"{x[1]} ({x[0]})",
                index=list(settings.SUPPORTED_LANGUAGES.keys()).index(settings.DEFAULT_LANGUAGE))

            style = st.selectbox("Animation Style", [
                "character – cute bouncing characters",
                "simple – floating shapes & stars",
                "nature – trees, flowers, outdoors",
                "abstract – geometric patterns",
            ])

            with st.expander("Advanced"):
                upload = st.checkbox("Upload to YouTube", False)
                privacy = st.selectbox("Privacy", ["private", "unlisted", "public"], index=0)
                bgm = st.checkbox("Background music", True)

            if st.form_submit_button("🚀 Generate Video", use_container_width=True, type="primary"):
                style_key = style.split(" –")[0]
                run_pipeline(topic=topic or rhyme, language=lang[0], scene_type=style_key,
                             upload=upload, privacy=privacy, bgm=bgm)

    with progress_col:
        st.subheader("Pipeline")

        step_statuses = get_step_statuses()
        for i, label in enumerate(steps_labels):
            s = step_statuses.get(i, "pending")
            if s == "completed":
                st.markdown(f"✅ **Step {i+1}:** {label}")
            elif s == "running":
                st.markdown(f"⏳ **Step {i+1}:** {label}")
            elif s == "error":
                st.markdown(f"❌ **Step {i+1}:** {label}")
            else:
                st.markdown(f"⬜ Step {i+1}: {label}")

        if st.session_state.logs:
            st.divider()
            with st.expander("Live Logs", expanded=True):
                for log in st.session_state.logs[-6:]:
                    st.caption(log)


def get_step_statuses():
    statuses = {}
    steps_map = [
        "content_planner", "script_writer", "scene_designer",
        "blender_renderer", "audio_generator", "video_composer",
        "thumbnail_creator", "seo_optimizer", "youtube_publisher",
    ]
    for log in st.session_state.logs:
        for i, name in enumerate(steps_map):
            if f"[{name}]" in log:
                statuses[i] = "completed"

    if st.session_state.status == "running":
        done = [k for k in statuses if statuses[k] == "completed"]
        nxt = max(done) + 1 if done else 0
        if nxt < 9:
            statuses[nxt] = "running"
    elif st.session_state.status == "done":
        for i in range(9):
            statuses[i] = "completed"

    return statuses


def run_pipeline(topic, language="en", scene_type="character",
                 upload=False, privacy="private", bgm=True):
    st.session_state.status = "running"
    st.session_state.logs = []

    project = create_initial_project(topic=topic, language=language)
    project["blender_config"]["scene_type"] = scene_type
    project["blender_config"]["background_music"] = bgm
    if upload:
        project.setdefault("youtube_metadata", {})["privacy_status"] = privacy

    state = AgentState(project=project)
    config = {"configurable": {"thread_id": f"ui_{datetime.now().timestamp()}"}}

    bar = st.progress(0, text="Starting...")

    try:
        for i, event in enumerate(agent.stream(state, config)):
            node_name = list(event.keys())[0]
            ns = event[node_name].get("project", {})
            s = ns.get("status", "processing")
            st.session_state.logs.append(f"[{node_name}] → {s}")
            bar.progress(min((i + 1) / 9, 1.0), text=f"{node_name}")
            time.sleep(0.05)

        st.session_state.status = "done"
        bar.progress(1.0, text="✅ Complete!")

        st.session_state.history.append({
            "rhyme": topic, "status": "completed",
            "time": datetime.now().strftime("%H:%M"),
        })

        st.success(f"✅ **{topic}** created!")

        fp = state.project.get("final_video_path", "")
        tp = state.project.get("thumbnail_path", "")
        meta = state.project.get("youtube_metadata", {})

        r1, r2, r3 = st.columns(3)
        if fp and Path(fp).exists():
            r1.metric("Video", f"{Path(fp).stat().st_size / 1024 / 1024:.1f} MB")
        if tp and Path(tp).exists():
            r2.image(tp, caption="Thumbnail", width=200)
        if meta and meta.get("title"):
            r3.markdown(f"**Title:** {meta['title'][:50]}...")

        st.balloons()

    except Exception as e:
        st.session_state.status = "error"
        st.session_state.logs.append(f"[ERROR] {e}")
        bar.progress(1.0, text="❌ Failed")
        st.error(f"Generation failed: {e}")
        st.session_state.history.append({
            "rhyme": topic, "status": "error",
            "time": datetime.now().strftime("%H:%M"),
        })


# ─── Batch Mode ─────────────────────────────────────────────────────────────────

def show_batch():
    st.title("📦 Batch Mode")

    tab1, tab2, tab3 = st.tabs(["Create Batch", "Content Calendar", "Results"])

    with tab1:
        num = st.number_input("Number of videos", 1, 20, 3)
        all_rhymes = get_rhyme_names()
        jobs = []

        for i in range(num):
            with st.expander(f"Video #{i + 1}", expanded=i == 0):
                topic_input = st.text_input("Topic", value="learn colors",
                                            placeholder="e.g., animal sounds, colors", key=f"bt_{i}")
                c1, c2 = st.columns(2)
                with c1:
                    r = st.selectbox("Or select a rhyme", [""] + all_rhymes, index=0, key=f"br_{i}")
                with c2:
                    l = st.selectbox("Language",
                        list(settings.SUPPORTED_LANGUAGES.keys()),
                        format_func=lambda x: settings.SUPPORTED_LANGUAGES.get(x, x),
                        key=f"bl_{i}")
                s = st.select_slider("Style", ["simple", "character", "nature", "abstract"],
                                     value="character", key=f"bs_{i}")
                u = st.checkbox("Upload", key=f"bu_{i}")
                jobs.append({"rhyme": r, "topic": topic_input or r, "language": l, "scene_type": s, "upload": u})

        if st.button("▶️ Run Batch", use_container_width=True, type="primary"):
            overall = st.progress(0, text="Starting batch...")
            for i, job in enumerate(jobs):
                st.markdown(f"**{i + 1}/{len(jobs)}:** {job['topic']}")
                jp = st.progress(0, text="")
                try:
                    project = create_initial_project(topic=job["topic"],
                                                     language=job["language"])
                    project["blender_config"]["scene_type"] = job["scene_type"]
                    state = AgentState(project=project)
                    cfg = {"configurable": {"thread_id": f"b{i}_{datetime.now().timestamp()}"}}
                    for j, ev in enumerate(agent.stream(state, cfg)):
                        jp.progress(min((j + 1) / 9, 1), text=list(ev.keys())[0])
                    st.session_state.batch_results.append({**job, "status": "completed"})
                    st.success(f"✅ {job['topic']}")
                except Exception as e:
                    st.session_state.batch_results.append({**job, "status": "error", "error": str(e)})
                    st.error(f"❌ {job['topic']}: {e}")
                overall.progress((i + 1) / len(jobs))
            st.success("🎉 Batch done!")

    with tab2:
        start = st.selectbox("Starting topic or rhyme", all_rhymes)
        weeks = st.slider("Weeks", 1, 12, 4)
        if st.button("Generate Calendar"):
            today = datetime.now()
            idx = all_rhymes.index(start)
            sched = []
            for w in range(weeks):
                sched.append({
                    "Week": w + 1,
                    "Topic": all_rhymes[(idx + w) % len(all_rhymes)],
                    "Date": (today + timedelta(weeks=w)).strftime("%b %d"),
                })
            st.dataframe(sched, use_container_width=True, hide_index=True)
            p = settings.OUTPUT_DIR / f"calendar_{today.strftime('%Y%m%d')}.json"
            p.write_text(json.dumps(sched, indent=2))
            st.success(f"Saved → `{p.name}`")

    with tab3:
        if st.session_state.batch_results:
            ok = sum(1 for r in st.session_state.batch_results if r["status"] == "completed")
            st.metric("Success Rate", f"{ok}/{len(st.session_state.batch_results)}")
            st.dataframe(st.session_state.batch_results, use_container_width=True, hide_index=True)
        else:
            st.info("No batch results.")


# ─── Upload Queue ────────────────────────────────────────────────────────────────

def show_queue():
    st.title("📤 Upload Queue")

    manifest = settings.OUTPUT_DIR / "upload_manifest.json"
    items = []
    if manifest.exists():
        try:
            d = json.loads(manifest.read_text())
            items = d if isinstance(d, list) else [d]
        except Exception:
            pass

    c1, c2, c3 = st.columns(3)
    c1.metric("Pending", len(items))
    c2.metric("Channel", settings.DEFAULT_CHANNEL_NAME)
    uploader = YouTubeUploader()
    c3.metric("API", "✅ Ready" if uploader.ready else "❌ Not configured")

    if items:
        for i, item in enumerate(items):
            with st.expander(f"#{i + 1}: {item.get('title', 'Untitled')[:70]}", expanded=i == 0):
                cols = st.columns(4)
                cols[0].markdown(f"**Privacy:** {item.get('privacy_status', '?')}")
                cols[1].markdown(f"**Schedule:** {item.get('publish_at', 'ASAP')[:16]}")
                cols[2].markdown(f"**Tags:** {len(item.get('tags', []))}")
                vp = item.get("video_path", "")
                cols[3].markdown(f"**File:** {'✅' if vp and Path(vp).exists() else '❌'}")

                if st.button("Upload Now", key=f"up_{i}", use_container_width=True):
                    u = YouTubeUploader()
                    if u.ready:
                        r = u.upload(vp, item["title"], item.get("description", ""),
                                     item.get("tags"), item.get("category_id", "24"),
                                     item.get("privacy_status", "public"),
                                     item.get("publish_at", ""), item.get("thumbnail_path"))
                        if r.get("success"):
                            st.success(f"✅ https://youtu.be/{r['video_id']}")
                            items.pop(i)
                            manifest.write_text(json.dumps(items, indent=2))
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {r.get('error', '?')}")
                    else:
                        st.error("YouTube API not configured.")
        if st.button("🗑️ Clear queue", use_container_width=True):
            manifest.write_text("[]")
            st.rerun()
    else:
        st.info("📪 Queue is empty. Generate a video with 'Upload to YouTube' checked.")


# ─── Rhymes ──────────────────────────────────────────────────────────────────────

def show_rhymes():
    st.title("📖 Rhyme Library")

    q = st.text_input("🔍 Search", placeholder="star, farm, wheels...")
    names = [r[0] for r in search_rhymes(q)] if q else get_rhyme_names()

    for name in names:
        data = RHYME_TEMPLATES.get(name, {})
        with st.expander(f"🎵 {name}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(data.get("description", ""))
                st.caption(
                    f"Age: {data.get('age_group', '?')}  ·  "
                    f"Duration: {data.get('duration', 120)}s  ·  "
                    f"Topics: {', '.join(data.get('topics', []))}"
                )
                lyrics = data.get("lyrics", {}).get("en", [])
                if lyrics:
                    st.text("\n".join(lyrics[:6]))
            with c2:
                langs = list(data.get("lyrics", {}).keys())
                st.markdown("**Available in:**")
                for lc in langs:
                    st.markdown(f"- {settings.SUPPORTED_LANGUAGES.get(lc, lc)}")
                if st.button("🎬 Create", key=f"cr_{name[:10]}", use_container_width=True):
                    st.session_state.page = "Create Video"
                    st.session_state.selected_rhyme = name
                    st.rerun()


# ─── Settings ────────────────────────────────────────────────────────────────────

def show_settings():
    st.title("⚙️ Settings")

    tabs = st.tabs(["General", "API Keys", "About"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Channel Name", settings.DEFAULT_CHANNEL_NAME)
        with c2:
            st.selectbox("Upload Schedule",
                         ["asap", "daily", "weekly", "biweekly", "monthly"],
                         index=["asap", "daily", "weekly", "biweekly", "monthly"].index(settings.UPLOAD_SCHEDULE))

        st.text_input("Blender Path", settings.BLENDER_EXECUTABLE)
        if Path(settings.BLENDER_EXECUTABLE).exists():
            st.success("✅ Blender found at path")
        else:
            st.warning("⚠️ Blender not found — placeholder images will be used for scenes")

        st.divider()
        st.metric("Videos Generated", count_videos())
        st.metric("Output Size",
                  f"{sum(f.stat().st_size for f in settings.VIDEOS_DIR.glob('*.mp4')) / 1024 / 1024:.0f} MB")

    with tabs[1]:
        fields = [
            ("YouTube Client ID", settings.YOUTUBE_CLIENT_ID, True),
            ("YouTube Client Secret", settings.YOUTUBE_CLIENT_SECRET, True),
            ("YouTube Refresh Token", settings.YOUTUBE_REFRESH_TOKEN, True),
            ("YouTube Channel ID", settings.YOUTUBE_CHANNEL_ID, False),
        ]
        for label, value, secret in fields:
            st.text_input(label, value=value or "",
                          type="password" if secret else "default")

        st.divider()
        st.subheader("ElevenLabs TTS")
        st.text_input("ElevenLabs API Key", value=settings.ELEVENLABS_API_KEY,
                      type="password", key="elevenlabs_key")
        st.text_input("ElevenLabs Voice ID", value=settings.ELEVENLABS_VOICE_ID,
                      key="elevenlabs_voice")
        st.caption("Leave empty to use gTTS (free) instead of ElevenLabs.")

        st.divider()
        from src.tools.blender_tools import find_blender
        sc1, sc2, sc3 = st.columns(3)
        sc1.markdown(f"**YouTube:** {'✅' if settings.YOUTUBE_CLIENT_ID else '❌'}")
        sc2.markdown(f"**Blender:** {'✅' if find_blender() else '❌'}")
        sc3.markdown(f"**ElevenLabs:** {'✅' if settings.ELEVENLABS_API_KEY else '❌ (using gTTS)'}")

    with tabs[2]:
        st.markdown("""
        **Kids Video Agent** v0.1.0

        Built with:
        - **LangGraph** — agent orchestration pipeline
        - **Blender** — 3D scene rendering (optional)
        - **TTS** — text-to-speech narration (gTTS or ElevenLabs)
        - **YouTube Data API** — video publishing
        - **Streamlit** — dashboard UI

        **Pipeline:** Content Planner → Script Writer → Scene Designer →
        Blender Renderer → Audio Generator → Video Composer →
        Thumbnail Creator → SEO Optimizer → YouTube Publisher
        """)


# ─── Router ─────────────────────────────────────────────────────────────────────

page_handlers = {
    "Dashboard": show_dashboard,
    "Create Video": show_create,
    "Batch Mode": show_batch,
    "Upload Queue": show_queue,
    "Rhymes": show_rhymes,
    "Settings": show_settings,
}

handler = page_handlers.get(st.session_state.page, show_dashboard)
handler()

# 🎬 Kids Video Agent

An AI-powered video creation agent for kids' YouTube channels. Built with **LangGraph**, **Blender**, and **OpenAI**.

## What It Does

The agent automates the entire video production pipeline:

1. **Content Planning** — Picks trending rhymes, writes scripts, designs storyboards
2. **3D Scene Generation** — Auto-generates Blender Python scripts for colorful kids' animations
3. **Audio Production** — Text-to-speech narration + background music
4. **Video Composition** — Stitches rendered clips with audio
5. **Thumbnail Creation** — Generates eye-catching YouTube thumbnails
6. **SEO Optimization** — Auto-generates titles, descriptions, tags, keywords
7. **YouTube Upload** — Publishes with scheduling

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# List available rhymes
python src/main.py list-rhymes

# Create a video
python src/main.py create "Twinkle Twinkle Little Star" --scene-type character

# Create and upload
python src/main.py create "Old MacDonald Had a Farm" --upload --privacy unlisted
```

## Commands

| Command | Description |
|---------|-------------|
| `create <rhyme>` | Generate a single video |
| `batch <file>` | Process multiple videos from JSON |
| `list-rhymes` | Show all built-in nursery rhymes |
| `search <query>` | Find rhymes by name or topic |
| `status` | Show config and output stats |
| `queue` | Manage YouTube upload queue |
| `schedule <rhyme>` | Generate a content calendar |
| `suggest` | Get AI trending content ideas |

## Architecture

```
src/
├── agent/
│   ├── graph.py          # LangGraph workflow definition
│   ├── state.py          # Typed state management
│   ├── conditions.py     # Edge routing conditions
│   └── nodes/
│       ├── content_planner.py
│       ├── script_writer.py
│       ├── scene_designer.py
│       ├── blender_renderer.py
│       ├── audio_generator.py
│       ├── video_composer.py
│       ├── thumbnail_creator.py
│       ├── seo_optimizer.py
│       └── youtube_publisher.py
├── tools/
│   ├── tts_tools.py      # Text-to-speech
│   ├── youtube_tools.py   # YouTube API
│   └── asset_manager.py   # Asset registry
├── templates/
│   ├── rhymes.py          # 6 built-in rhymes in 4 languages
│   └── blender/           # Blender Python script generators
└── main.py                # CLI entry point
```

## Configuration

Set these in `.env`:

- `OPENAI_API_KEY` — For content planning, scripts, SEO
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` — For auto-upload
- `BLENDER_EXECUTABLE` — Path to Blender (for 3D rendering)
- `DEFAULT_LANGUAGE` — en, es, fr, hi

## Requirements

- Python 3.11+
- Blender 4.0+ (optional — creates placeholders without it)
- ffmpeg (optional — for video composition)

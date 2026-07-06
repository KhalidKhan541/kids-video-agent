# Kids Video Agent - AI Agent Instructions

## Project Overview
Automated kids video production pipeline using LangGraph + free tools.

## Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run pipeline locally
python run_pipeline.py

# Run tests
pytest tests/ -v

# Lint
ruff check src/ agents/

# Type check
mypy src/ agents/
```

## Skill Loading (AUTOMATIC)
**Always run skill-router at task start.** Load relevant skills before beginning work.
- Read `~/.config/opencode/skills/skill-router/skill-triggers.json`
- Match user request to skill triggers
- Load matched skills automatically
- Follow loaded skill instructions

## Working Rules
1. **Load skills first** - Use skill-router to detect relevant skills
2. **Always run tests** before claiming done
3. **Always lint** before committing
4. **Update progress.md** after completing a feature
5. **One feature at a time** - don't overreach
6. **Verify email sent** before marking video complete

## Definition of Done
- [ ] Code changes complete
- [ ] Tests pass
- [ ] Lint passes
- [ ] Type check passes
- [ ] progress.md updated
- [ ] Email notification sent (if video generated)

## Architecture
- `src/tools/` - Tool implementations (groq, image, voice, music, ffmpeg, email)
- `agents/` - LangGraph agent nodes
- `src/agent/` - Graph workflow and state
- `.github/workflows/` - GitHub Actions automation

## Common Pitfalls
- Pollinations.ai rate limit: ~80 images/day
- Groq rate limit: 30 RPM
- SMTP requires app password, not regular password
- FFmpeg must be installed for video composition

## Verification Commands
```bash
# Check all tools import correctly
python -c "from src.tools import groq_tools, image_tools, piper_tts_tools, music_tools, ffmpeg_tools, email_tools; print('All tools OK')"

# Check pipeline runs
python run_pipeline.py --dry-run

# Check email config
python -c "from src.tools.email_tools import send_completion_email; print('Email ready')"
```
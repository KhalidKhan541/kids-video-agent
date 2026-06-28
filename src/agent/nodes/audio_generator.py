"""Audio generator — creates narration using ElevenLabs or gTTS."""

from pathlib import Path
from src.config import settings
from src.agent.state import AgentState
from src.tools.tts_tools import generate_narration, add_background_music, combine_audio_segments


class AudioGeneratorNode:
    def __call__(self, state: AgentState) -> dict:
        proj = state.project
        scenes = proj.get("scenes", [])
        lang = proj.get("language", "en")
        topic = proj.get("topic", "video")

        stem = topic.replace(" ", "_").lower()
        audio_dir = settings.AUDIO_DIR / stem

        narration_paths = []
        for i, scene in enumerate(scenes):
            text = scene.get("narration_text", "")
            if not text.strip():
                continue
            audio_path = audio_dir / f"narration_{i+1:03d}.wav"
            generate_narration(text, audio_path, lang=lang)
            if audio_path.exists():
                narration_paths.append(audio_path)

        combined_path = settings.AUDIO_DIR / f"{stem}_combined.wav"
        if narration_paths:
            combine_audio_segments(narration_paths, combined_path)
        else:
            self._write_silent_wav(combined_path, duration=30)

        final_path = settings.AUDIO_DIR / f"{stem}_final.wav"
        if combined_path.exists():
            add_background_music(combined_path, final_path)
        else:
            final_path = combined_path

        return {
            "project": {
                **proj,
                "audio_path": str(final_path) if final_path.exists() else str(combined_path),
                "status": "audio_generated",
            },
            "logs": [
                f"[Audio] Generated {len(narration_paths)} narration segments",
                f"[Audio] Combined and added background music",
            ],
        }

    def _write_silent_wav(self, path: Path, duration: int = 30):
        import wave, struct
        path.parent.mkdir(parents=True, exist_ok=True)
        sr = 22050
        num = sr * duration
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            for _ in range(0, num, 1024):
                chunk = min(1024, num - _)
                wf.writeframes(struct.pack(f"<{chunk}h", *([0] * chunk)))

# VersaScribe

A local-first CLI for capturing, transcribing, and analyzing meetings on macOS.

- **Private by default** — transcription runs entirely on your machine via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) or [GigaAM](https://github.com/salute-developers/GigaAM)
- **System audio capture** — records all meeting audio (Zoom, Meet, Teams, etc.) via [BlackHole](https://github.com/ExistentialAudio/BlackHole)
- **Speaker diarization** — optional local speaker identification via [WhisperX](https://github.com/m-bain/whisperX) + pyannote.audio
- **Claude integration** — optional AI features: Minutes of Meeting, trend analysis across meetings
- **Flat-file storage** — transcripts are plain JSON files; portable, git-friendly, zero lock-in

---

## Quick start

```bash
# 1. Prerequisites (once)
brew install blackhole-2ch ffmpeg python@3.11

# 2. Set up BlackHole audio routing (see docs/SETUP.md)

# 3. Install VersaScribe
pip install -e .

# 4. Optional: enable Claude features
vs config --set claude_api_key=sk-ant-...

# 5. Optional: enable speaker diarization
pip install 'versascribe[diarize]'
vs config --set hf_token=hf_...   # free token from huggingface.co

# 5b. Optional: use GigaAM for Russian / multilingual transcription
pip install 'versascribe[gigaam]'
vs config --set transcription_backend=gigaam

# 6. Record a meeting
vs record --title "Weekly Sync" --project backend --participant Alice --participant Bob

# 7. List, search, generate MoM
vs list
vs search "action items"
vs mom <transcript-id>
```

---

## Documentation

| File | Description |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | BlackHole setup, prerequisites, installation |
| [docs/USAGE.md](docs/USAGE.md) | All commands with examples |
| [docs/AGENTS.md](docs/AGENTS.md) | Claude integration — MoM, trend analysis, prompts |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Architecture, data model, module design |

---

## Commands at a glance

```
vs record          Capture system audio and transcribe
vs import FILE     Transcribe a .mp3 / .mp4 / .m4a / .wav / .webm file
vs list            Browse transcripts with filters
vs show ID         Read a transcript or its MoM
vs search QUERY    Full-text search across all transcripts
vs tag ID          Edit projects, participants, tags, title, speaker map
vs replay ID       Interactive TUI: navigate, edit, assign speakers, add notes, play audio
vs mom ID          Generate Minutes of Meeting (Claude)
vs analyze         Trend analysis across a set of meetings (Claude)
vs config          Manage settings
vs delete ID       Remove a transcript
```

---

## Requirements

- macOS 12+
- Python 3.11+
- [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) — for `vs record`
- [ffmpeg](https://ffmpeg.org) — for `vs import` with video or non-WAV audio
- An [Anthropic API key](https://console.anthropic.com) — for `vs mom` and `vs analyze` (optional)
- A [HuggingFace token](https://hf.co/settings/tokens) + `pip install 'versascribe[diarize]'` — for speaker diarization (optional)
- `pip install 'versascribe[gigaam]'` — for GigaAM transcription backend, best for Russian (optional)

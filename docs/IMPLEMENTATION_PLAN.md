# Implementation Plan & Architecture

## Overview

VersaScribe is a Python CLI tool for capturing, transcribing, and analyzing meetings on macOS. It is designed to be local-first: transcription runs entirely on-device with no network access unless Claude features are explicitly invoked.

---

## Technology choices

| Concern | Choice | Rationale |
|---|---|---|
| CLI framework | Typer + Rich | Typer gives clean function-signature-driven commands; Rich handles all terminal output |
| Audio capture | sounddevice + BlackHole | sounddevice wraps PortAudio (CoreAudio on macOS); BlackHole is the standard virtual audio device for macOS system audio capture |
| Audio I/O | soundfile + numpy | soundfile writes PCM WAV reliably; numpy needed by sounddevice callbacks |
| Audio extraction | ffmpeg (system binary) | Handles every container format; invoked via subprocess |
| Transcription | faster-whisper | CTranslate2 backend; 4× faster than openai-whisper on CPU with int8 quantization; supports word timestamps natively |
| AI features | anthropic SDK | Official Python SDK; Messages API |
| Data validation | Pydantic v2 | JSON schema enforcement, alias support (`$schema`), atomic serialization via `model_dump_json` |
| Storage | Flat JSON files | Zero dependencies; portable; git-friendly; sufficient for personal-scale use |
| Build | hatchling + pyproject.toml | Modern Python packaging standard |

---

## Project layout

```
versascribe/
├── pyproject.toml                    # build, deps, entry point (vs = versascribe.cli:app)
├── README.md
├── docs/
│   ├── SETUP.md
│   ├── USAGE.md
│   ├── AGENTS.md
│   └── IMPLEMENTATION_PLAN.md
├── src/versascribe/
│   ├── __init__.py                   # VersaScribeError hierarchy
│   ├── cli.py                        # root Typer app, startup checks, sub-command registration
│   ├── context.py                    # get_config() / set_config() — separated to avoid circular imports
│   ├── config.py                     # AppConfig (Pydantic), load_config(), save_config()
│   ├── display.py                    # all Rich output helpers (no business logic)
│   ├── commands/
│   │   ├── record.py                 # vs record
│   │   ├── import_.py                # vs import
│   │   ├── list_.py                  # vs list
│   │   ├── show.py                   # vs show
│   │   ├── search.py                 # vs search
│   │   ├── tag.py                    # vs tag
│   │   ├── mom.py                    # vs mom
│   │   ├── analyze.py                # vs analyze
│   │   ├── config.py                 # vs config
│   │   └── delete.py                 # vs delete
│   ├── audio/
│   │   ├── recorder.py               # AudioRecorder: threading + sounddevice + soundfile
│   │   ├── extractor.py              # ffmpeg wrapper for audio/video extraction
│   │   └── devices.py                # sounddevice query helpers
│   ├── transcription/
│   │   └── whisper.py                # faster-whisper wrapper, module-level model cache
│   ├── storage/
│   │   ├── paths.py                  # filesystem helpers, slug generation, path construction
│   │   ├── transcript.py             # Pydantic models + load_transcript() / save_transcript()
│   │   └── index.py                  # build_index(), filter_transcripts(), search_transcripts(), resolve_id()
│   └── ai/
│       ├── client.py                 # get_client() with ClaudeNotConfiguredError guard
│       ├── mom.py                    # MoM prompt builder and generate_mom()
│       └── analysis.py               # analysis prompt builder and generate_analysis()
└── tests/
    ├── conftest.py                   # shared fixtures, make_transcript_file() helper
    ├── fixtures/
    │   └── sample_transcript.json
    ├── unit/                         # 57 tests, no hardware or API required
    │   ├── test_storage.py
    │   ├── test_index.py
    │   ├── test_config.py
    │   ├── test_transcription.py
    │   ├── test_mom_prompt.py
    │   └── test_analysis_prompt.py
    └── integration/
        ├── test_import_wav.py        # marker: slow (downloads Whisper model)
        └── test_ai_roundtrip.py      # marker: api (requires ANTHROPIC_API_KEY)
```

---

## Data model

Every transcript is one JSON file at `~/.versascribe/YYYYMMDD_HHMMSS_<slug>.json`.

```
TranscriptRecord
├── id: str                           # == filename stem
├── version: int                      # schema version, currently 1
├── created_at / updated_at: datetime
├── source: SourceInfo
│   ├── type: "recording" | "import"
│   ├── original_filename: str | null  # set for imports
│   ├── audio_file: str | null         # relative path within storage root
│   └── duration_seconds: float
├── metadata: TranscriptMetadata
│   ├── title: str
│   ├── project: list[str]            # plain string tags
│   ├── participants: list[str]
│   ├── tags: list[str]
│   ├── language: str | null
│   └── whisper_model: str | null
├── transcription: TranscriptionData
│   ├── engine: "faster-whisper"
│   ├── model_size: str
│   ├── language_detected: str
│   ├── language_probability: float
│   ├── segments: list[TranscriptSegment]
│   │   └── {id, start, end, text, avg_logprob, no_speech_prob, words?: list[WordTimestamp]}
│   └── full_text: str                # pre-joined for fast preview/search
└── analysis: AnalysisBlock
    └── mom: MomRecord | null
        ├── generated_at: datetime
        ├── model: str
        └── content: MomContent
            ├── meeting_title, date, duration_minutes
            ├── attendees, agenda
            ├── discussion_points: [{topic, summary}]
            ├── decisions: [str]
            ├── action_items: [{owner, task, due_date}]
            └── next_meeting, notes
```

Projects, participants, and tags are plain string arrays — there are no separate entity files. This keeps the schema simple and the storage portable.

---

## Audio pipeline

### Recording (vs record)

```
macOS meeting audio (Zoom, Meet, Teams, etc.)
    ↓  [macOS Multi-Output Device routes audio to both speakers and BlackHole]
BlackHole 2ch virtual audio device
    ↓
sounddevice.InputStream(
    device=blackhole_device_index,
    samplerate=16000,         # Whisper's native sample rate
    channels=1,               # downmix to mono
    dtype="float32",
    blocksize=4096,           # ~256ms chunks
    callback=_audio_callback,
)
    ↓  [audio callback — non-blocking, runs on PortAudio thread]
threading.Queue[np.ndarray]   # indata.copy() via put_nowait(); peak level for level meter
    ↓  [writer thread]
soundfile.SoundFile(wav_path, mode="w", samplerate=16000, subtype="PCM_16")
    ↓  [Ctrl-C → SIGINT handler → recorder.stop() → stop_event.set()]
    ↓  [writer thread drains remaining queue frames before closing file]
~/.versascribe/audio/YYYYMMDD_HHMMSS_<slug>.wav
    ↓
transcribe_audio(wav_path, ...)
    ↓
TranscriptRecord saved to ~/.versascribe/YYYYMMDD_HHMMSS_<slug>.json
```

Key design decisions:
- `put_nowait()` (not `put()`) ensures the audio callback never blocks — dropped frames are counted but the callback never stalls
- The writer thread drains the queue fully after `stop_event` is set, so the final audio frames are not lost
- `blocksize=4096` at 16kHz = 256ms per callback; balances latency with overhead

### Import (vs import)

```
input file (.mp4 / .webm / .m4a / .mp3 / .wav)
    ↓  [if not already 16kHz mono WAV]
ffmpeg -i {input} -vn -ar 16000 -ac 1 -c:a pcm_s16le -y {tmp_wav}
    ↓
transcribe_audio(tmp_wav, ...)
    ↓  [tmp file deleted]
TranscriptRecord saved
```

---

## Indexing strategy

There is no database. `build_index(storage_dir)` scans all `*.json` files in the storage directory and reads each one to extract `IndexEntry` fields (everything except the `segments` array). For 500 transcripts this takes under 200ms on a modern machine.

Filtering is pure Python list comprehension with set intersection for multi-value fields (project, participant, tag). Full-text search loads only the transcripts that passed the filter, then scans segment text with case-insensitive substring matching.

A mtime-gated index cache at `~/.versascribe/.index_cache.json` is available as a future optimization but is not required for typical collection sizes.

---

## Circular import solution

Commands need `get_config()` (which reads from the Typer context), and `cli.py` needs to import the commands to register them. The naive approach creates a circular import.

**Solution:** `get_config()` and `set_config()` live in `versascribe/context.py`, which has no imports from within the package. Commands import from `context.py`. `cli.py` imports from `context.py` and from the commands (at module level, after the `app` is defined).

---

## Error hierarchy

All package-specific errors inherit from `VersaScribeError` (in `__init__.py`). The CLI's startup callback wraps every command in a try/except that catches known error types and renders them as styled Rich panels:

```
VersaScribeError
├── DeviceNotFoundError     → "Audio device not found" panel + device list hint
├── FFmpegNotFoundError     → "ffmpeg not found" panel + brew install hint
├── ExtractionError         → generic error panel with ffmpeg stderr
├── ClaudeNotConfiguredError → "Claude not configured" panel + config command hint
└── TranscriptNotFoundError → "Transcript not found" panel
```

---

## Testing

```bash
# Fast (no hardware, no API, no model download) — 57 tests
python3.11 -m pytest tests/unit -m "not slow and not api and not audio"

# Include integration tests (downloads ~74MB Whisper model on first run)
python3.11 -m pytest -m "not api and not audio"

# All tests including Claude API calls
ANTHROPIC_API_KEY=sk-ant-... python3.11 -m pytest

# With coverage report
python3.11 -m pytest tests/unit -m "not slow and not api" --cov=versascribe --cov-report=term-missing
```

Test markers:
- `slow` — requires Whisper model download
- `api` — requires `ANTHROPIC_API_KEY` environment variable
- `audio` — requires audio hardware and BlackHole

---

## Extending VersaScribe

### Adding a new command

1. Create `src/versascribe/commands/mycommand.py` with a `app = typer.Typer(...)` and a `@app.callback(invoke_without_command=True)` function
2. Import `get_config` from `versascribe.context` (not `versascribe.cli`)
3. Register in `cli.py`: `app.add_typer(mycommand.app, name="mycommand")`
4. Add to the imports list in `cli.py`

### Adding a new config key

1. Add a field to `AppConfig` in `config.py`
2. Add the key name to `VALID_KEYS` in `config.py`
3. `vs config --set` and `vs config --list` will pick it up automatically

### Adding a new AI feature

1. Create `src/versascribe/ai/myfeature.py` with a prompt builder and a `generate_*` function
2. Accept `client: anthropic.Anthropic` and relevant `TranscriptRecord` objects
3. Call `client.messages.create(model=model, max_tokens=..., system=..., messages=[...])`
4. Parse the response through `_extract_json()` (strips accidental markdown fences) before `json.loads()`
5. Validate with a Pydantic model if the output schema is structured

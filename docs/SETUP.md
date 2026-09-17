# Setup Guide

## Prerequisites

### 1. Python 3.11+

```bash
brew install python@3.11
python3.11 --version   # should print 3.11.x or higher
```

### 2. ffmpeg

Required for importing video files (`.mp4`, `.mov`, `.webm`) and non-WAV audio. Not needed for `vs record`.

```bash
brew install ffmpeg
ffmpeg -version   # verify
```

### 3. BlackHole 2ch

BlackHole is a virtual audio device. It lets macOS route system audio (Zoom, Meet, Teams, Safari, etc.) to VersaScribe for recording.

```bash
brew install blackhole-2ch
```

#### Configure a Multi-Output Device

After installing BlackHole, you need to create a **Multi-Output Device** that sends audio to both your speakers/headphones and BlackHole simultaneously. This lets you hear the meeting while VersaScribe captures it.

1. Open **Audio MIDI Setup** (search in Spotlight)
2. Click **+** in the bottom-left → **Create Multi-Output Device**
3. Tick both **BlackHole 2ch** and your normal output (e.g. MacBook Pro Speakers or your headphones)
4. Name it something like `VersaScribe Output`
5. Right-click the new device → **Use This Device For Sound Output**
6. In **System Settings → Sound → Output**, select `VersaScribe Output`

From now on, all system audio is heard normally **and** routed through BlackHole so VersaScribe can capture it.

> **Tip:** Set a keyboard shortcut or menu-bar toggle to quickly switch your output back to speakers-only when you're not recording.

---

## Install VersaScribe

```bash
# Clone or navigate to the project directory
cd /path/to/versascribe

# Install with dev dependencies (recommended while developing)
python3.11 -m pip install -e ".[dev]"

# Or just the tool
python3.11 -m pip install -e .

# Verify
vs --help
```

---

## First-run configuration

```bash
# See all config values and their defaults
vs config --list

# (Optional) Set a Claude API key for MoM and analysis features
vs config --set claude_api_key=sk-ant-api03-...

# (Optional) Change the default Whisper model
# Options: tiny, base, small, medium, large-v2, large-v3
# base (~74 MB) is a good default; small (~244 MB) is noticeably better
vs config --set whisper_model=small

# (Optional) Change the BlackHole device name if yours differs
vs config --list   # check blackhole_device value
vs config --set blackhole_device="BlackHole 2ch"
```

---

## Speaker diarization (optional)

Diarization identifies who spoke when, labelling each segment with `SPEAKER_00`, `SPEAKER_01`, etc.

### 1. Install the diarize extra

```bash
pip install 'versascribe[diarize]'
```

This pulls in [WhisperX](https://github.com/m-bain/whisperX) and PyTorch (~2 GB total, one-time).

> **torch 2.2.x users:** `transformers>=4.45` requires torch 2.5+ and disables PyTorch automatically when an older version is present, causing a `NameError: name 'torch' is not defined` crash. Pin it down:
> ```bash
> pip install "transformers<4.45"
> ```

> **Dual OpenMP crash (SIGSEGV/EXC_BAD_ACCESS):** PyTorch and faster-whisper (ctranslate2) each bundle their own `libiomp5.dylib`. Two runtimes in the same process crash when their thread pools try to synchronise across each other's structures. VersaScribe sets `KMP_DUPLICATE_LIB_OK=TRUE` and `OMP_NUM_THREADS=1` automatically before either library loads, which prevents the crash. Transcription is single-threaded as a result, but there is no practical speed regression on CPU hardware where parallelism is already limited.

### 2. Get a HuggingFace token

Diarization uses [pyannote.audio](https://github.com/pyannote/pyannote-audio), which requires accepting its license:

1. Create a free account at <https://huggingface.co>
2. Generate a token at <https://hf.co/settings/tokens>
3. Accept the model terms at <https://hf.co/pyannote/speaker-diarization-3.1>

### 3. Save the token

```bash
vs config --set hf_token=hf_xxxxxxxxxxxxxxxx
```

The model (~1 GB) downloads automatically on first diarized transcription.

### 4. (Optional) Enable by default

```bash
vs config --set diarize_by_default=true
```

### 5. Map speaker labels to names

Diarization labels speakers anonymously (`SPEAKER_00`, `SPEAKER_01`, …). After recording, map them to real names:

```bash
vs tag <id> --map-speaker "SPEAKER_00=Alice" --map-speaker "SPEAKER_01=Bob"
```

The mapping is stored in the transcript. `vs show --timestamps` then displays names instead of labels.

### Whisper model sizes

| Model | Size | Speed (CPU) | Quality |
|---|---|---|---|
| tiny | 39 MB | Fastest | Basic |
| base | 74 MB | Fast | Good for clear audio |
| small | 244 MB | Moderate | Better accuracy |
| medium | 769 MB | Slow | High accuracy |
| large-v3 | 1.5 GB | Very slow | Best available |

Models are downloaded automatically on first use from HuggingFace and cached at `~/.cache/huggingface/hub/`.

---

## GigaAM transcription backend (optional)

[GigaAM](https://github.com/salute-developers/GigaAM) is a Conformer-based ASR model from Sber with state-of-the-art quality on Russian. Use it instead of Whisper when your meetings are primarily in Russian or other CIS languages.

Available model variants:

| Model | Languages | Notes |
|---|---|---|
| `v3_e2e_rnnt` | Russian | Best quality, with punctuation (default) |
| `v3_e2e_ctc` | Russian | CTC alternative, with punctuation |
| `v3_rnnt` / `v3_ctc` | Russian | Without built-in punctuation |
| `multilingual_ctc` | 70+ languages | Best for mixed-language meetings |
| `multilingual_large_ctc` | 70+ languages | Higher accuracy, ~1.2 GB |

Short aliases `rnnt` and `ctc` resolve to `v3_rnnt` and `v3_ctc` respectively.

### 1. Install the gigaam extra

The PyPI release only covers v1/v2 models. VersaScribe pulls gigaam directly from the GitHub repo to get v3 and multilingual:

```bash
pip install 'versascribe[gigaam]'
```

This installs gigaam from GitHub, PyTorch (≥2.0), and pyannote.audio for long-form VAD segmentation.

> **Older PyTorch / corporate mirrors:** The `[gigaam]` extra requires only `torch>=2.0.0`, so torch 2.2.x (the maximum on many corporate pip mirrors) works fine. VersaScribe patches two upstream incompatibilities at runtime: the `torch.serialization.safe_globals` API absent before torch 2.4, and a gigaam/pyannote.audio path-handling mismatch introduced in pyannote 3.x. No manual workarounds are needed.

> **NumPy compatibility:** PyTorch 2.x requires `numpy<2`. The `[gigaam]` extra pins `numpy<2` automatically. If you already have NumPy 2.x installed, downgrade it:
> ```bash
> pip install "numpy<2"
> ```

### 2. Set a HuggingFace token

GigaAM uses pyannote models for both long-form transcription (VAD) and speaker diarization. Both require accepting the respective model licenses on HuggingFace.

If you already set `hf_token` for Whisper diarization, no further action is needed.

Otherwise:
1. Create a free account at <https://huggingface.co>
2. Generate a token at <https://hf.co/settings/tokens>
3. Accept model terms at <https://hf.co/pyannote/segmentation-3.0> (VAD — required for longform)
4. Accept model terms at <https://hf.co/pyannote/speaker-diarization-3.1> (required for `--diarize`)
5. `vs config --set hf_token=hf_xxxxxxxxxxxxxxxx`

Without an HF token, GigaAM falls back to single-chunk transcription (no segment timing), which works poorly for anything longer than a minute.

### 3. Enable GigaAM

```bash
# Use as default backend
vs config --set transcription_backend=gigaam

# Or switch model (v3_e2e_rnnt is default)
vs config --set gigaam_model=multilingual_ctc
```

Models are downloaded automatically on first use and cached at `~/.cache/huggingface/hub/`.

### Performance note

GigaAM transcription (without diarization) takes roughly **1–2 minutes per 5 minutes of audio** on a modern Intel CPU, which is acceptable for post-meeting processing.

Speaker diarization (`--diarize`) adds the pyannote embedding pipeline on top and is **significantly slower on CPU** — expect 5–7× real-time (e.g. ~25 minutes for a 4-minute recording). This is a hardware limitation of running the WeSpeaker embedding model on CPU, not a software issue. Practical workarounds:

- Transcribe without `--diarize`, then assign speakers manually in `vs replay` (press `S` on a segment)
- Run `vs import --diarize` as a background task after the meeting and come back to it later

---

## Verify the setup

```bash
# Check available audio input devices
vs record --list-devices

# You should see "BlackHole 2ch" in the list
# If not, check that BlackHole is installed and the Multi-Output Device is set up

# Run a quick import test (no BlackHole needed)
vs import /path/to/any-audio.mp3 --title "Test"
vs list
```

---

## Storage location

All data lives in `~/.versascribe/`:

```
~/.versascribe/
├── config.json           # your settings
├── audio/                # raw WAV recordings
├── tmp/                  # temporary extraction files (auto-cleaned)
└── *.json                # transcript files
```

Override the storage path:

```bash
vs config --set storage_path=/Volumes/ExternalDrive/versascribe
```

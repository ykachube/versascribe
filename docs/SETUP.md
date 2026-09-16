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

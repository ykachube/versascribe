"""Extract audio from video or non-WAV audio files using ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from versascribe import ExtractionError, FFmpegNotFoundError

_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".flac", ".opus", ".webm"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
_WAV_EXT = ".wav"


def needs_extraction(path: Path) -> bool:
    """Return True if the file is not already a 16kHz mono WAV."""
    suffix = path.suffix.lower()
    if suffix != _WAV_EXT:
        return True
    import soundfile as sf

    try:
        info = sf.info(str(path))
        return info.samplerate != 16000 or info.channels != 1
    except Exception:
        return True


def extract_to_wav(
    source: Path,
    output_dir: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    if not shutil.which("ffmpeg"):
        raise FFmpegNotFoundError("ffmpeg not found in PATH.")

    suffix = source.suffix.lower()
    if suffix not in _AUDIO_EXTENSIONS and suffix not in _VIDEO_EXTENSIONS and suffix != _WAV_EXT:
        raise ExtractionError(f"Unsupported file type: {suffix}")

    output = output_dir / (source.stem + "_extracted.wav")
    cmd = [
        "ffmpeg",
        "-i", str(source),
        "-vn",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        "-y",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise ExtractionError(
            f"ffmpeg failed (exit {result.returncode}):\n"
            + result.stderr.decode(errors="replace")
        )
    return output

"""GigaAM transcription backend (salute-developers/GigaAM)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from versascribe.storage.transcript import TranscriptSegment
from versascribe.transcription.whisper import TranscriptionResult

_model_cache: dict[str, object] = {}


def get_model(model_name: str):
    if model_name not in _model_cache:
        try:
            import gigaam
        except ImportError:
            raise ImportError(
                "gigaam is required for the GigaAM backend. "
                "Install with: pip install 'versascribe[gigaam]'"
            )
        _model_cache[model_name] = gigaam.load_model(model_name)
    return _model_cache[model_name]


def transcribe_audio_gigaam(
    audio_path: Path,
    model_name: str = "v3_e2e_rnnt",
    word_timestamps: bool = False,
    hf_token: Optional[str] = None,
) -> TranscriptionResult:
    model = get_model(model_name)
    audio_str = str(audio_path)

    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        raw = model.transcribe_longform(audio_str)
        segments = [
            TranscriptSegment(id=i, start=seg.start, end=seg.end, text=seg.text)
            for i, seg in enumerate(raw)
        ]
    elif word_timestamps:
        raw = model.transcribe(audio_str, word_timestamps=True)
        segments = [
            TranscriptSegment(id=i, start=w.start, end=w.end, text=w.text)
            for i, w in enumerate(raw.words)
        ]
    else:
        text = str(model.transcribe(audio_str))
        segments = [TranscriptSegment(id=0, start=0.0, end=0.0, text=text)]

    full_text = " ".join(s.text.strip() for s in segments)
    lang = "multilingual" if "multilingual" in model_name else "ru"
    return TranscriptionResult(
        segments=segments,
        language_detected=lang,
        language_probability=1.0,
        model_size=model_name,
        full_text=full_text,
    )

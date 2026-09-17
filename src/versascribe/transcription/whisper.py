"""faster-whisper wrapper with optional WhisperX speaker diarization."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from versascribe.storage.transcript import TranscriptSegment, WordTimestamp

_model_cache: dict[str, object] = {}


@dataclass
class TranscriptionResult:
    segments: list[TranscriptSegment]
    language_detected: str
    language_probability: float
    model_size: str
    full_text: str = field(default="")


def get_model(size: str):
    if size not in _model_cache:
        from faster_whisper import WhisperModel

        _model_cache[size] = WhisperModel(size, device="cpu", compute_type="int8")
    return _model_cache[size]


def transcribe_audio(
    audio_path: Path,
    model_size: str = "base",
    word_timestamps: bool = False,
    language: Optional[str] = None,
    beam_size: int = 5,
    diarize: bool = False,
    hf_token: Optional[str] = None,
    num_speakers: Optional[int] = None,
) -> TranscriptionResult:
    if diarize:
        return _transcribe_with_diarization(
            audio_path, model_size, language, hf_token, num_speakers
        )
    return _transcribe_plain(audio_path, model_size, word_timestamps, language, beam_size)


def _transcribe_plain(
    audio_path: Path,
    model_size: str,
    word_timestamps: bool,
    language: Optional[str],
    beam_size: int,
) -> TranscriptionResult:
    model = get_model(model_size)
    segments_gen, info = model.transcribe(
        str(audio_path),
        beam_size=beam_size,
        word_timestamps=word_timestamps,
        language=language,
    )

    pydantic_segments: list[TranscriptSegment] = []
    for i, seg in enumerate(segments_gen):
        words = None
        if word_timestamps and seg.words:
            words = [
                WordTimestamp(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    probability=w.probability,
                )
                for w in seg.words
            ]
        pydantic_segments.append(
            TranscriptSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                avg_logprob=seg.avg_logprob,
                compression_ratio=seg.compression_ratio,
                no_speech_prob=seg.no_speech_prob,
                words=words,
            )
        )

    full_text = " ".join(s.text.strip() for s in pydantic_segments)
    return TranscriptionResult(
        segments=pydantic_segments,
        language_detected=info.language,
        language_probability=info.language_probability,
        model_size=model_size,
        full_text=full_text,
    )


def _transcribe_with_diarization(
    audio_path: Path,
    model_size: str,
    language: Optional[str],
    hf_token: Optional[str],
    num_speakers: Optional[int],
) -> TranscriptionResult:
    try:
        import whisperx
    except ImportError:
        raise ImportError(
            "whisperx is required for diarization. "
            "Install with: pip install 'versascribe[diarize]'"
        )

    if not hf_token:
        raise ValueError(
            "A HuggingFace token is required for diarization (pyannote.audio).\n"
            "Get one free at https://hf.co/settings/tokens and run:\n"
            "  vs config --set hf_token=YOUR_TOKEN\n"
            "Accept model terms at: https://hf.co/pyannote/speaker-diarization-3.1"
        )

    device = "cpu"
    audio = whisperx.load_audio(str(audio_path))

    # Step 1: transcribe
    model = whisperx.load_model(model_size, device, compute_type="int8", language=language)
    result = model.transcribe(audio, batch_size=8)

    # Step 2: align for word-level timestamps (needed by diarization)
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, device, return_char_alignments=False
    )

    # Step 3: diarize
    # Set HF_TOKEN env var so pyannote/hf_hub_download picks it up;
    # avoid use_auth_token= which was removed in recent huggingface_hub.
    import os
    os.environ["HF_TOKEN"] = hf_token
    diarize_model = whisperx.DiarizationPipeline(device=device)
    kwargs = {}
    if num_speakers:
        kwargs["min_speakers"] = num_speakers
        kwargs["max_speakers"] = num_speakers
    diarize_segments = diarize_model(audio, **kwargs)

    # Step 4: assign speaker labels to each word/segment
    result = whisperx.assign_word_speakers(diarize_segments, result)

    pydantic_segments: list[TranscriptSegment] = []
    for i, seg in enumerate(result["segments"]):
        pydantic_segments.append(
            TranscriptSegment(
                id=i,
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                speaker=seg.get("speaker"),
            )
        )

    full_text = " ".join(s.text.strip() for s in pydantic_segments)
    lang = result.get("language", "unknown")
    return TranscriptionResult(
        segments=pydantic_segments,
        language_detected=lang,
        language_probability=1.0,
        model_size=model_size,
        full_text=full_text,
    )

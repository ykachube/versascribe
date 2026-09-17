"""GigaAM transcription backend (salute-developers/GigaAM)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from versascribe.storage.transcript import TranscriptSegment
from versascribe.transcription.whisper import TranscriptionResult

_model_cache: dict[str, object] = {}


def _patch_torch_compat() -> None:
    """Add torch.serialization.safe_globals no-op for torch < 2.4."""
    import contextlib
    import torch.serialization as _ts
    if not hasattr(_ts, "safe_globals"):
        @contextlib.contextmanager
        def _safe_globals(_globals):
            yield
        _ts.safe_globals = _safe_globals  # type: ignore[attr-defined]


def _patch_hf_hub_compat() -> None:
    """Rename use_auth_token -> token everywhere for huggingface_hub >= 0.20.

    Older pyannote.audio calls hf_hub_download(use_auth_token=...) which was
    removed. Patch the function in huggingface_hub itself and replace every
    direct reference already bound in loaded modules (pyannote has several).
    """
    import sys
    import functools
    import huggingface_hub as _hf

    _orig = _hf.hf_hub_download
    if getattr(_orig, "_use_auth_patched", False):
        return

    @functools.wraps(_orig)
    def _patched(*args, **kwargs):
        if "use_auth_token" in kwargs:
            kwargs.setdefault("token", kwargs.pop("use_auth_token"))
        return _orig(*args, **kwargs)

    _patched._use_auth_patched = True  # type: ignore[attr-defined]
    _hf.hf_hub_download = _patched

    for mod in list(sys.modules.values()):
        if mod is not None and getattr(mod, "hf_hub_download", None) is _orig:
            mod.hf_hub_download = _patched


def _patch_gigaam_vad() -> None:
    """Fix gigaam's load_segmentation_model for pyannote>=3.1.

    gigaam passes the snapshot directory to Model.from_pretrained, but pyannote
    only accepts a file path or a HF repo ID — never a directory.  Pass
    pytorch_model.bin from inside the snapshot instead.
    """
    import os
    import gigaam.vad_utils as _vad
    from pyannote.audio import Model

    _orig = _vad.load_segmentation_model

    def _patched(model_id: str) -> Model:
        import torch.serialization as _ts
        local_dir = _vad.resolve_local_segmentation_path(model_id)
        checkpoint = os.path.join(local_dir, "pytorch_model.bin")
        if not os.path.isfile(checkpoint):
            raise FileNotFoundError(
                f"pytorch_model.bin not found in snapshot {local_dir}. "
                "Try clearing the HuggingFace cache and re-running."
            )
        with _ts.safe_globals([]):
            return Model.from_pretrained(checkpoint)

    _vad.load_segmentation_model = _patched


def get_model(model_name: str):
    if model_name not in _model_cache:
        try:
            import gigaam
        except ImportError:
            raise ImportError(
                "gigaam is required for the GigaAM backend. "
                "Install with: pip install 'versascribe[gigaam]'"
            )
        _patch_torch_compat()
        _patch_hf_hub_compat()
        _patch_gigaam_vad()
        _model_cache[model_name] = gigaam.load_model(model_name)
    return _model_cache[model_name]


def _diarize_with_pyannote(audio_path: Path, hf_token: str, num_speakers: Optional[int] = None):
    """Run pyannote speaker diarization and return an Annotation object."""
    from pyannote.audio import Pipeline

    os.environ["HF_TOKEN"] = hf_token
    # Re-run the patch now that pyannote.audio sub-modules are fully loaded
    # (they weren't imported yet when get_model first called _patch_hf_hub_compat).
    _patch_hf_hub_compat()
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    kwargs: dict = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    return pipeline(str(audio_path), **kwargs)


def _assign_speakers(segments: list, diarization) -> list:
    """Assign the dominant speaker label to each segment by timestamp overlap."""
    turns = list(diarization.itertracks(yield_label=True))
    result = []
    for seg in segments:
        overlap: dict[str, float] = {}
        for turn, _, speaker in turns:
            lo = max(seg.start, turn.start)
            hi = min(seg.end, turn.end)
            if hi > lo:
                overlap[speaker] = overlap.get(speaker, 0.0) + (hi - lo)
        best = max(overlap, key=overlap.__getitem__) if overlap else None
        result.append(seg.model_copy(update={"speaker": best}))
    return result


def transcribe_audio_gigaam(
    audio_path: Path,
    model_name: str = "v3_e2e_rnnt",
    word_timestamps: bool = False,
    hf_token: Optional[str] = None,
    diarize: bool = False,
    num_speakers: Optional[int] = None,
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

    if diarize:
        if not hf_token:
            raise ValueError(
                "hf_token is required for diarization. "
                "Set it with: vs config --set hf_token=hf_..."
            )
        diarization = _diarize_with_pyannote(audio_path, hf_token, num_speakers)
        segments = _assign_speakers(segments, diarization)

    full_text = " ".join(s.text.strip() for s in segments)
    lang = "multilingual" if "multilingual" in model_name else "ru"
    return TranscriptionResult(
        segments=segments,
        language_detected=lang,
        language_probability=1.0,
        model_size=model_name,
        full_text=full_text,
    )

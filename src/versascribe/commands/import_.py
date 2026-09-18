"""vs import — ingest an audio or video file and transcribe it."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer

from versascribe.audio.extractor import extract_to_wav, needs_extraction
from versascribe.context import get_config
from versascribe.display import console, success, transcription_progress
from versascribe.prompts import prompt_metadata
from versascribe.storage.paths import get_audio_dir, new_transcript_path
from versascribe.storage.transcript import (
    AnalysisBlock,
    SourceInfo,
    TranscriptionData,
    TranscriptMetadata,
    TranscriptRecord,
    save_transcript,
)

_SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".mov", ".mkv", ".wav", ".webm", ".aac", ".flac", ".ogg"}


def import_file(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="Audio or video file to import"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Meeting title (default: filename)"),
    project: List[str] = typer.Option([], "--project", "-p", help="Project tag (repeatable)"),
    participant: List[str] = typer.Option([], "--participant", help="Participant name (repeatable)"),
    tag: List[str] = typer.Option([], "--tag", help="Tag (repeatable)"),
    model: Optional[str] = typer.Option(None, "--model", help="Whisper model size"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Transcription backend: whisper or gigaam"),
    gigaam_model: Optional[str] = typer.Option(None, "--gigaam-model", help="GigaAM model (overrides config)"),
    language: Optional[str] = typer.Option(None, "--language", help="Force transcription language"),
    word_timestamps: bool = typer.Option(False, "--word-timestamps", help="Enable word-level timestamps"),
    link_audio: bool = typer.Option(
        False,
        "--link-audio",
        help="Store the absolute source path instead of copying the audio",
    ),
    diarize: bool = typer.Option(False, "--diarize", help="Identify speakers (requires whisperx + HF token)"),
    num_speakers: Optional[int] = typer.Option(None, "--num-speakers", help="Expected number of speakers"),
) -> None:
    """Import an audio or video file and transcribe it."""
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        console.print(f"[red]Unsupported file type:[/red] {path.suffix}")
        console.print(f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}")
        raise typer.Exit(1)

    config = get_config(ctx)
    model_size = model or config.whisper_model
    wt = word_timestamps or config.word_timestamps
    default_title = path.stem.replace("_", " ").replace("-", " ").title()

    # Full wizard when no metadata flags are provided.
    if not title and not project and not participant and not tag:
        info = prompt_metadata(
            default_title=default_title,
            show_diarize=not diarize and bool(config.hf_token),
        )
        meeting_title = info["title"]
        project = list(info["project"])
        participant = list(info["participant"])
        tag = list(info["tag"])
        if not diarize:
            diarize = info["diarize"]
    else:
        meeting_title = title or default_title

    now = datetime.now(timezone.utc)
    tmp_dir = config.storage_dir / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    wav_path = path
    extracted = False
    if needs_extraction(path):
        console.print(f"[dim]Extracting audio from[/dim] {path.name}[dim]…[/dim]")
        wav_path = extract_to_wav(path, tmp_dir)
        extracted = True

    try:
        import soundfile as sf
        info_obj = sf.info(str(wav_path))
        duration_seconds = info_obj.duration
    except Exception:
        duration_seconds = 0.0

    effective_backend = backend or config.transcription_backend
    with transcription_progress() as progress:
        if effective_backend == "gigaam":
            from versascribe.transcription.gigaam import transcribe_audio_gigaam
            should_diarize = diarize or config.diarize_by_default
            effective_gigaam_model = gigaam_model or config.gigaam_model
            task_id = progress.add_task(f"Transcribing with GigaAM [{effective_gigaam_model}]…", total=None)
            result = transcribe_audio_gigaam(
                wav_path, effective_gigaam_model, wt, config.hf_token,
                diarize=should_diarize, num_speakers=num_speakers,
            )
        else:
            from versascribe.transcription.whisper import transcribe_audio
            task_id = progress.add_task(f"Transcribing with Whisper [{model_size}]…", total=None)
            should_diarize = diarize or config.diarize_by_default
            result = transcribe_audio(
                wav_path, model_size, wt, language,
                diarize=should_diarize,
                hf_token=config.hf_token,
                num_speakers=num_speakers,
            )
        progress.update(task_id, completed=True)

    if extracted:
        try:
            wav_path.unlink()
        except Exception:
            pass

    transcript_path = new_transcript_path(config.storage_dir, meeting_title, now)
    if link_audio:
        relative_audio = str(path.resolve())
    else:
        audio_dir = get_audio_dir(config)
        audio_suffix = ".wav" if extracted else path.suffix.lower()
        stored_audio_path = audio_dir / f"{transcript_path.stem}{audio_suffix}"
        if extracted:
            shutil.move(str(wav_path), str(stored_audio_path))
        else:
            shutil.copy2(path, stored_audio_path)
        relative_audio = str(stored_audio_path.relative_to(config.storage_dir))

    record_obj = TranscriptRecord(
        **{
            "$schema": "versascribe/transcript/v1",
            "id": transcript_path.stem,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "source": SourceInfo(
                type="import",
                original_filename=path.name,
                duration_seconds=duration_seconds,
                audio_file=relative_audio,
                sample_rate=16000,
                channels=1,
            ),
            "metadata": TranscriptMetadata(
                title=meeting_title,
                project=list(project),
                participants=list(participant),
                tags=list(tag),
                language=result.language_detected,
                whisper_model=model_size,
            ),
            "transcription": TranscriptionData(
                model_size=result.model_size,
                language_detected=result.language_detected,
                language_probability=result.language_probability,
                segments=result.segments,
                full_text=result.full_text,
            ),
            "analysis": AnalysisBlock(),
        }
    )
    save_transcript(record_obj, transcript_path)
    success(f"Transcript saved: [bold]{transcript_path.name}[/bold]")
    console.print(
        f"[dim]ID:[/dim] {record_obj.id}  [dim]Duration:[/dim] {duration_seconds:.0f}s  "
        f"[dim]Language:[/dim] {result.language_detected}"
    )

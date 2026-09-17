"""vs record — capture system audio via BlackHole and transcribe."""

from __future__ import annotations

import signal
from datetime import datetime, timezone
from typing import List, Optional

import typer

from versascribe.audio.devices import find_device, list_devices
from versascribe.audio.recorder import AudioRecorder
from versascribe.context import get_config
from versascribe.display import console, make_recording_live, success, transcription_progress
from versascribe.prompts import prompt_metadata
from versascribe.storage.paths import new_audio_path, new_transcript_path
from versascribe.storage.transcript import (
    AnalysisBlock,
    SourceInfo,
    TranscriptMetadata,
    TranscriptRecord,
    TranscriptionData,
    save_transcript,
)


def record(
    ctx: typer.Context,
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Meeting title"),
    project: List[str] = typer.Option([], "--project", "-p", help="Project tag (repeatable)"),
    participant: List[str] = typer.Option([], "--participant", help="Participant name (repeatable)"),
    tag: List[str] = typer.Option([], "--tag", help="Tag (repeatable)"),
    device: Optional[str] = typer.Option(None, "--device", help="Audio device name"),
    model: Optional[str] = typer.Option(None, "--model", help="Whisper model size"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Transcription backend: whisper or gigaam"),
    gigaam_model: Optional[str] = typer.Option(None, "--gigaam-model", help="GigaAM model (overrides config)"),
    word_timestamps: bool = typer.Option(False, "--word-timestamps", help="Enable word-level timestamps"),
    no_transcribe: bool = typer.Option(False, "--no-transcribe", help="Save audio only, skip transcription"),
    language: Optional[str] = typer.Option(None, "--language", help="Force transcription language"),
    list_devs: bool = typer.Option(False, "--list-devices", help="List available input devices and exit"),
    diarize: bool = typer.Option(False, "--diarize", help="Identify speakers (requires whisperx + HF token)"),
    num_speakers: Optional[int] = typer.Option(None, "--num-speakers", help="Expected number of speakers"),
) -> None:
    """Record system audio and transcribe."""
    if list_devs:
        devs = list_devices()
        console.print("[bold]Available input devices:[/bold]")
        for d in devs:
            if d["max_input_channels"] > 0:
                console.print(f"  [{d['index']}] {d['name']}")
        return

    config = get_config(ctx)
    device_name = device or config.blackhole_device
    model_size = model or config.whisper_model
    wt = word_timestamps or config.word_timestamps

    # Full wizard when no metadata flags are provided; single title prompt otherwise.
    if not title and not project and not participant and not tag:
        info = prompt_metadata(
            default_title="Untitled Meeting",
            show_diarize=not diarize and bool(config.hf_token),
        )
        title = info["title"]
        project = list(info["project"])
        participant = list(info["participant"])
        tag = list(info["tag"])
        if not diarize:
            diarize = info["diarize"]
    elif not title:
        title = Prompt.ask("[bold]Meeting title[/bold]", default="Untitled Meeting")

    now = datetime.now(timezone.utc)
    audio_dir = config.storage_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    wav_path = new_audio_path(audio_dir, title, now)

    device_index = find_device(device_name)
    recorder = AudioRecorder(wav_path, device_index)

    stopped = False

    def _on_sigint(sig, frame):
        nonlocal stopped
        if not stopped:
            stopped = True
            recorder.stop()

    signal.signal(signal.SIGINT, _on_sigint)

    console.print(f"[dim]Recording to:[/dim] {wav_path.name}")
    console.print("[dim]Press Ctrl-C to stop.[/dim]\n")

    recorder.start()
    with make_recording_live(recorder.get_peak_level, recorder.get_elapsed):
        recorder.wait()

    console.print()

    try:
        import soundfile as sf
        info = sf.info(str(wav_path))
        duration_seconds = info.duration
    except Exception:
        duration_seconds = 0.0

    if no_transcribe:
        console.print(f"[bold]Audio saved:[/bold] {wav_path}")
        return

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

    transcript_path = new_transcript_path(config.storage_dir, title, now)
    relative_audio = str(wav_path.relative_to(config.storage_dir))

    record_obj = TranscriptRecord(
        **{
            "$schema": "versascribe/transcript/v1",
            "id": transcript_path.stem,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "source": SourceInfo(
                type="recording",
                audio_file=relative_audio,
                duration_seconds=duration_seconds,
                audio_device=device_name,
                sample_rate=16000,
                channels=1,
            ),
            "metadata": TranscriptMetadata(
                title=title,
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
    console.print(f"[dim]ID: {record_obj.id}[/dim]")

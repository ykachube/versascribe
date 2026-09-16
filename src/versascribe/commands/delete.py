"""vs delete — remove a transcript (and optionally its audio)."""

from __future__ import annotations

import typer
from rich.prompt import Confirm

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import console, success
from versascribe.storage.index import resolve_id
from versascribe.storage.transcript import load_transcript


def delete(
    ctx: typer.Context,
    transcript_id: str = typer.Argument(..., help="Transcript ID or prefix"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    keep_audio: bool = typer.Option(False, "--keep-audio", help="Keep the raw audio WAV file"),
) -> None:
    """Delete a transcript and optionally its audio file."""
    config = get_config(ctx)
    try:
        path = resolve_id(transcript_id, config.storage_dir)
    except (FileNotFoundError, ValueError) as e:
        raise TranscriptNotFoundError(str(e))

    record = load_transcript(path)

    if not yes:
        confirmed = Confirm.ask(
            f"Delete [bold]{record.metadata.title}[/bold] ({record.id})?",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            return

    audio_path = None
    if not keep_audio and record.source.audio_file:
        audio_path = config.storage_dir / record.source.audio_file

    path.unlink(missing_ok=True)

    if audio_path and audio_path.exists():
        audio_path.unlink(missing_ok=True)
        success(f"Deleted transcript and audio: [bold]{record.id}[/bold]")
    else:
        success(f"Deleted transcript: [bold]{record.id}[/bold]")

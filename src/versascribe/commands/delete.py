"""vs delete — remove a transcript (and optionally its audio)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.prompt import Confirm
from rich.table import Table

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import console, success
from versascribe.storage.index import build_index, filter_transcripts, resolve_id
from versascribe.storage.transcript import load_transcript


def _delete_one(path: Path, keep_audio: bool, storage_dir: Path) -> tuple[str, bool]:
    """Delete a single transcript file and optionally its audio. Returns (id, audio_deleted)."""
    record = load_transcript(path)
    audio_deleted = False
    if not keep_audio and record.source.audio_file:
        audio_path = storage_dir / record.source.audio_file
        if audio_path.exists():
            audio_path.unlink(missing_ok=True)
            audio_deleted = True
    path.unlink(missing_ok=True)
    return record.id, audio_deleted


def delete(
    ctx: typer.Context,
    transcript_id: Optional[str] = typer.Argument(None, help="Transcript ID or prefix"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", help="Delete all transcripts with this tag (repeatable)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    keep_audio: bool = typer.Option(False, "--keep-audio", help="Keep the raw audio WAV file"),
) -> None:
    """Delete a transcript and optionally its audio file.

    Either pass a transcript ID, or use --tag to bulk-delete all matching transcripts.
    """
    config = get_config(ctx)

    # ── bulk delete by tag ──────────────────────────────────────────────────
    if tag:
        index = build_index(config.storage_dir)
        entries = filter_transcripts(index, tags=tag)
        if not entries:
            console.print(f"[yellow]No transcripts found with tag(s): {', '.join(tag)}[/yellow]")
            raise typer.Exit()

        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("ID", style="dim")
        table.add_column("Title")
        table.add_column("Tags")
        for e in entries:
            table.add_row(e.id, e.title, ", ".join(e.tags))
        console.print(table)
        console.print()

        if not yes:
            confirmed = Confirm.ask(
                f"Delete [bold]{len(entries)}[/bold] transcript(s)?",
                default=False,
            )
            if not confirmed:
                console.print("[dim]Cancelled.[/dim]")
                raise typer.Exit()

        n_audio = 0
        for e in entries:
            _, audio_deleted = _delete_one(e.path, keep_audio, config.storage_dir)
            if audio_deleted:
                n_audio += 1

        audio_note = f" and {n_audio} audio file(s)" if n_audio else ""
        success(f"Deleted {len(entries)} transcript(s){audio_note}.")
        return

    # ── single delete by ID ─────────────────────────────────────────────────
    if not transcript_id:
        console.print("[red]Provide a transcript ID or --tag to delete by tag.[/red]")
        raise typer.Exit(code=1)

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

    _, audio_deleted = _delete_one(path, keep_audio, config.storage_dir)
    if audio_deleted:
        success(f"Deleted transcript and audio: [bold]{record.id}[/bold]")
    else:
        success(f"Deleted transcript: [bold]{record.id}[/bold]")

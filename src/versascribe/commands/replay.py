"""vs replay — interactive TUI for reviewing and editing a recorded meeting."""

from __future__ import annotations

from typing import Optional

import typer

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import console, success
from versascribe.storage.index import build_index, resolve_id
from versascribe.storage.transcript import load_transcript


def replay(
    ctx: typer.Context,
    transcript_id: Optional[str] = typer.Argument(None, help="Transcript ID or prefix (omit for latest)"),
    debug_audio: bool = typer.Option(False, "--debug-audio", help="Write audio debug log to ~/.versascribe/audio_debug.log"),
) -> None:
    """
    Interactively replay a meeting: navigate segments, edit text,
    assign speakers, add sidenotes, and play back audio.

    Omit the ID to open the most recently recorded meeting.
    """
    from versascribe.replay import audio as _audio
    from versascribe.replay.app import ReplayApp

    config = get_config(ctx)
    if debug_audio:
        _audio.configure_log(config.storage_dir)

    if transcript_id is None:
        index = build_index(config.storage_dir)
        if not index:
            console.print("[yellow]No transcripts found.[/yellow]")
            raise typer.Exit()
        from datetime import timezone
        def _as_utc(dt):
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        latest = max(index, key=lambda e: _as_utc(e.created_at))
        path = latest.path
    else:
        try:
            path = resolve_id(transcript_id, config.storage_dir)
        except (FileNotFoundError, ValueError) as e:
            raise TranscriptNotFoundError(str(e))

    record = load_transcript(path)
    app = ReplayApp(record, path)
    saved = app.run()

    if saved:
        success(f"Changes saved to [bold]{record.id}[/bold]")
    else:
        console.print("[dim]No changes.[/dim]")

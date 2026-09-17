"""vs replay — interactive TUI for reviewing and editing a recorded meeting."""

from __future__ import annotations

import typer

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import console, success
from versascribe.storage.index import resolve_id
from versascribe.storage.transcript import load_transcript


def replay(
    ctx: typer.Context,
    transcript_id: str = typer.Argument(..., help="Transcript ID or unambiguous prefix"),
    debug_audio: bool = typer.Option(False, "--debug-audio", help="Write audio debug log to ~/.versascribe/audio_debug.log"),
) -> None:
    """
    Interactively replay a meeting: navigate segments, edit text,
    assign speakers, add sidenotes, and play back audio.
    """
    from versascribe.replay import audio as _audio
    from versascribe.replay.app import ReplayApp

    config = get_config(ctx)
    if debug_audio:
        _audio.configure_log(config.storage_dir)
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

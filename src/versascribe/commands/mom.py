"""vs mom — generate or display Minutes of Meeting for a transcript."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from versascribe import TranscriptNotFoundError
from versascribe.ai.client import get_client
from versascribe.ai.mom import generate_mom
from versascribe.context import get_config
from versascribe.display import console, render_mom, success, transcription_progress
from versascribe.storage.index import resolve_id
from versascribe.storage.transcript import load_transcript, save_transcript


def mom(
    ctx: typer.Context,
    transcript_id: str = typer.Argument(..., help="Transcript ID or prefix"),
    model: Optional[str] = typer.Option(None, "--model", help="Claude model to use"),
    fmt: str = typer.Option("text", "--format", "-f", help="text|json|markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write to file instead of stdout"),
    regenerate: bool = typer.Option(False, "--regenerate", help="Force regeneration even if cached"),
) -> None:
    """Generate or show Minutes of Meeting."""
    config = get_config(ctx)
    try:
        path = resolve_id(transcript_id, config.storage_dir)
    except (FileNotFoundError, ValueError) as e:
        raise TranscriptNotFoundError(str(e))

    record = load_transcript(path)
    claude_model = model or config.claude_model

    if record.analysis.mom and not regenerate:
        console.print("[dim]Using cached MoM (use --regenerate to refresh)[/dim]\n")
        mom_record = record.analysis.mom
    else:
        client = get_client(config)
        with transcription_progress() as progress:
            task_id = progress.add_task(f"Generating MoM with [{claude_model}]…", total=None)
            mom_record = generate_mom(client, record, claude_model)
            progress.update(task_id, completed=True)

        record.analysis.mom = mom_record
        record.updated_at = datetime.now(timezone.utc)
        save_transcript(record, path)
        success("MoM generated and cached.")
        console.print()

    if output:
        if fmt == "json":
            output.write_text(mom_record.content.model_dump_json(indent=2), encoding="utf-8")
        else:
            from io import StringIO
            from rich.console import Console as RichConsole
            buf = StringIO()
            tmp_console = RichConsole(file=buf, highlight=False, markup=False)
            output.write_text(buf.getvalue(), encoding="utf-8")
        success(f"Written to: {output}")
    else:
        render_mom(mom_record.content, fmt)

"""vs show — display a transcript or its MoM."""

from __future__ import annotations

import json
from typing import Optional

import typer

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import console, render_mom, render_transcript_text
from versascribe.storage.index import resolve_id
from versascribe.storage.transcript import load_transcript


def show(
    ctx: typer.Context,
    transcript_id: str = typer.Argument(..., help="Transcript ID or unambiguous prefix"),
    fmt: str = typer.Option("text", "--format", "-f", help="text|json|segments"),
    timestamps: bool = typer.Option(False, "--timestamps", "-t", help="Prefix each segment with [MM:SS]"),
    mom: bool = typer.Option(False, "--mom", help="Show MoM instead of transcript"),
) -> None:
    """Show a transcript or its MoM."""
    config = get_config(ctx)
    try:
        path = resolve_id(transcript_id, config.storage_dir)
    except (FileNotFoundError, ValueError) as e:
        raise TranscriptNotFoundError(str(e))

    record = load_transcript(path)

    if mom:
        if not record.analysis.mom:
            console.print("[yellow]No MoM generated yet. Run:[/yellow] vs mom " + record.id)
            raise typer.Exit(1)
        render_mom(record.analysis.mom.content, fmt)
        return

    if fmt == "json":
        console.print_json(json.dumps(record.model_dump_for_save(), indent=2))
    elif fmt == "segments":
        for seg in record.transcription.segments:
            m, s = divmod(int(seg.start), 60)
            console.print(
                f"[dim][{m:02d}:{s:02d}–{int(seg.end // 60):02d}:{int(seg.end % 60):02d}][/dim] "
                f"{seg.text.strip()}"
            )
    else:
        render_transcript_text(record, timestamps)

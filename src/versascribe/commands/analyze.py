"""vs analyze — run trend analysis across a set of transcripts via Claude."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Optional

import typer

from versascribe.ai.client import get_client
from versascribe.ai.analysis import generate_analysis
from versascribe.context import get_config
from versascribe.display import console, render_analysis, success, transcription_progress
from versascribe.storage.index import build_index, filter_transcripts
from versascribe.storage.transcript import load_transcript


def analyze(
    ctx: typer.Context,
    project: List[str] = typer.Option([], "--project", "-p"),
    participant: List[str] = typer.Option([], "--participant"),
    tag: List[str] = typer.Option([], "--tag"),
    since: Optional[str] = typer.Option(None, "--since"),
    until: Optional[str] = typer.Option(None, "--until"),
    all_transcripts: bool = typer.Option(False, "--all", help="Ignore filters, use all transcripts"),
    focus: Optional[str] = typer.Option(None, "--focus", help="Specific analysis directive"),
    model: Optional[str] = typer.Option(None, "--model"),
    fmt: str = typer.Option("text", "--format", "-f", help="text|json|markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    min_count: int = typer.Option(2, "--min-count", help="Minimum matching transcripts required"),
) -> None:
    """Analyze trends across meetings using Claude."""
    config = get_config(ctx)
    claude_model = model or config.claude_model
    client = get_client(config)

    index = build_index(config.storage_dir)
    since_date = date.fromisoformat(since) if since else None
    until_date = date.fromisoformat(until) if until else None

    if all_transcripts:
        filtered = index
    else:
        filtered = filter_transcripts(
            index,
            project=list(project) or None,
            participants=list(participant) or None,
            tags=list(tag) or None,
            since=since_date,
            until=until_date,
        )

    if len(filtered) < min_count:
        console.print(
            f"[yellow]Only {len(filtered)} transcript(s) match (minimum {min_count}). "
            f"Use --min-count 1 to proceed anyway.[/yellow]"
        )
        raise typer.Exit(1)

    console.print(f"[dim]Analyzing {len(filtered)} transcript(s)…[/dim]")
    records = []
    for entry in filtered:
        try:
            records.append(load_transcript(entry.path))
        except Exception:
            continue

    with transcription_progress() as progress:
        task_id = progress.add_task(f"Running analysis with [{claude_model}]…", total=None)
        result = generate_analysis(client, records, focus, claude_model)
        progress.update(task_id, completed=True)

    if output:
        import json
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        success(f"Analysis written to: {output}")
    else:
        render_analysis(result, fmt)

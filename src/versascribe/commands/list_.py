"""vs list — list transcripts with filters."""

from __future__ import annotations

import json
from datetime import date
from typing import List, Optional

import typer

from versascribe.context import get_config
from versascribe.display import console, render_transcript_table
from versascribe.storage.index import build_index, filter_transcripts
from versascribe.storage.transcript import load_transcript


def list_transcripts(
    ctx: typer.Context,
    project: List[str] = typer.Option([], "--project", "-p", help="Filter by project (repeatable)"),
    participant: List[str] = typer.Option([], "--participant", help="Filter by participant (repeatable)"),
    tag: List[str] = typer.Option([], "--tag", help="Filter by tag (repeatable)"),
    since: Optional[str] = typer.Option(None, "--since", help="YYYY-MM-DD lower bound"),
    until: Optional[str] = typer.Option(None, "--until", help="YYYY-MM-DD upper bound"),
    has_mom: Optional[bool] = typer.Option(None, "--has-mom/--no-mom", help="Filter by MoM presence"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results"),
    fmt: str = typer.Option("table", "--format", "-f", help="table|json|ids"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Open the interactive transcript browser"
    ),
) -> None:
    """List transcripts with optional filters."""
    config = get_config(ctx)
    index = build_index(config.storage_dir)

    since_date = date.fromisoformat(since) if since else None
    until_date = date.fromisoformat(until) if until else None

    entries = filter_transcripts(
        index,
        project=list(project) or None,
        participants=list(participant) or None,
        tags=list(tag) or None,
        since=since_date,
        until=until_date,
        has_mom=has_mom,
    )[:limit]

    if interactive:
        from versascribe.replay.app import ReplayApp
        from versascribe.replay.list_app import TranscriptListApp

        while True:
            selected_path = TranscriptListApp(config.storage_dir, entries).run()
            if selected_path is None:
                return
            record = load_transcript(selected_path)
            ReplayApp(record, selected_path).run()

    if fmt == "json":
        console.print_json(
            json.dumps(
                [
                    {
                        "id": e.id,
                        "title": e.title,
                        "created_at": e.created_at.isoformat(),
                        "project": e.project,
                        "participants": e.participants,
                        "tags": e.tags,
                        "duration_seconds": e.duration_seconds,
                        "has_mom": e.has_mom,
                        "audio_file": e.audio_file,
                    }
                    for e in entries
                ],
                indent=2,
            )
        )
    elif fmt == "ids":
        for e in entries:
            console.print(e.id)
    else:
        console.print(f"[dim]Showing {len(entries)} transcript(s)[/dim]\n")
        render_transcript_table(entries)

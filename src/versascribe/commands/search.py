"""vs search — full-text search across transcripts."""

from __future__ import annotations

import json
from datetime import date
from typing import List, Optional

import typer

from versascribe.context import get_config
from versascribe.display import console, render_search_results
from versascribe.storage.index import build_index, filter_transcripts, search_transcripts


def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    project: List[str] = typer.Option([], "--project", "-p"),
    participant: List[str] = typer.Option([], "--participant"),
    tag: List[str] = typer.Option([], "--tag"),
    since: Optional[str] = typer.Option(None, "--since"),
    until: Optional[str] = typer.Option(None, "--until"),
    fmt: str = typer.Option("text", "--format", "-f", help="text|json"),
) -> None:
    """Search transcript text."""
    config = get_config(ctx)
    index = build_index(config.storage_dir)
    since_date = date.fromisoformat(since) if since else None
    until_date = date.fromisoformat(until) if until else None

    filtered = filter_transcripts(
        index,
        project=list(project) or None,
        participants=list(participant) or None,
        tags=list(tag) or None,
        since=since_date,
        until=until_date,
    )
    results = search_transcripts(query, filtered, config.storage_dir)

    if fmt == "json":
        out = [
            {"id": e.id, "title": e.title, "matches": matches}
            for e, matches in results
        ]
        console.print_json(json.dumps(out, indent=2))
    else:
        render_search_results(results, query)

"""vs tag — add/remove metadata tags on a transcript."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import typer

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import success
from versascribe.storage.index import resolve_id
from versascribe.storage.transcript import load_transcript, save_transcript


def tag(
    ctx: typer.Context,
    transcript_id: str = typer.Argument(..., help="Transcript ID or prefix"),
    add_tag: List[str] = typer.Option([], "--add-tag"),
    remove_tag: List[str] = typer.Option([], "--remove-tag"),
    add_project: List[str] = typer.Option([], "--add-project"),
    remove_project: List[str] = typer.Option([], "--remove-project"),
    add_participant: List[str] = typer.Option([], "--add-participant"),
    remove_participant: List[str] = typer.Option([], "--remove-participant"),
    title: Optional[str] = typer.Option(None, "--title"),
) -> None:
    """Add or remove tags, projects, participants, or update title."""
    config = get_config(ctx)
    try:
        path = resolve_id(transcript_id, config.storage_dir)
    except (FileNotFoundError, ValueError) as e:
        raise TranscriptNotFoundError(str(e))

    record = load_transcript(path)
    meta = record.metadata

    if title:
        meta.title = title
    meta.tags = _apply(meta.tags, add_tag, remove_tag)
    meta.project = _apply(meta.project, add_project, remove_project)
    meta.participants = _apply(meta.participants, add_participant, remove_participant)
    record.updated_at = datetime.now(timezone.utc)

    save_transcript(record, path)
    success(f"Updated: [bold]{record.id}[/bold]")


def _apply(current: list[str], add: list[str], remove: list[str]) -> list[str]:
    result = list(current)
    for item in add:
        if item not in result:
            result.append(item)
    for item in remove:
        if item in result:
            result.remove(item)
    return result

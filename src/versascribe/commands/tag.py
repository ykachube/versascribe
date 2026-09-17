"""vs tag — add/remove metadata tags on a transcript."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import typer

from versascribe import TranscriptNotFoundError
from versascribe.context import get_config
from versascribe.display import console, success
from versascribe.storage.index import resolve_all
from versascribe.storage.transcript import load_transcript, save_transcript


def tag(
    ctx: typer.Context,
    transcript_id: str = typer.Argument(..., help="Transcript ID or prefix (applies to all matches)"),
    add_tag: List[str] = typer.Option([], "--add-tag"),
    remove_tag: List[str] = typer.Option([], "--remove-tag"),
    add_project: List[str] = typer.Option([], "--add-project"),
    remove_project: List[str] = typer.Option([], "--remove-project"),
    add_participant: List[str] = typer.Option([], "--add-participant"),
    remove_participant: List[str] = typer.Option([], "--remove-participant"),
    map_speaker: List[str] = typer.Option([], "--map-speaker", help="SPEAKER_00=Name (repeatable)"),
    title: Optional[str] = typer.Option(None, "--title"),
) -> None:
    """Add or remove tags, projects, participants, or update title.

    When the prefix matches multiple transcripts, the change is applied to all of them.
    """
    config = get_config(ctx)
    try:
        paths = resolve_all(transcript_id, config.storage_dir)
    except FileNotFoundError as e:
        raise TranscriptNotFoundError(str(e))

    speaker_map: dict[str, str] = {}
    for mapping in map_speaker:
        if "=" not in mapping:
            from versascribe.display import error_panel
            error_panel(f"Invalid format: {mapping!r}  Expected SPEAKER_XX=Name")
            raise typer.Exit(1)
        label, _, name = mapping.partition("=")
        speaker_map[label.strip()] = name.strip()

    updated = []
    for path in paths:
        record = load_transcript(path)
        meta = record.metadata

        if title:
            meta.title = title
        meta.tags = _apply(meta.tags, add_tag, remove_tag)
        meta.project = _apply(meta.project, add_project, remove_project)
        meta.participants = _apply(meta.participants, add_participant, remove_participant)
        meta.speaker_map.update(speaker_map)

        record.updated_at = datetime.now(timezone.utc)
        save_transcript(record, path)
        updated.append(record.id)

    if len(updated) == 1:
        success(f"Updated: [bold]{updated[0]}[/bold]")
    else:
        console.print(f"[green]Updated {len(updated)} transcripts:[/green]")
        for rid in updated:
            console.print(f"  [dim]{rid}[/dim]")


def _apply(current: list[str], add: list[str], remove: list[str]) -> list[str]:
    result = list(current)
    for item in add:
        if item not in result:
            result.append(item)
    for item in remove:
        if item in result:
            result.remove(item)
    return result

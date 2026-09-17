"""Index building, filtering, and full-text search over JSON transcript files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from versascribe.storage.transcript import TranscriptRecord, load_transcript


@dataclass
class IndexEntry:
    id: str
    path: Path
    created_at: datetime
    title: str
    project: list[str]
    participants: list[str]
    tags: list[str]
    duration_seconds: float
    has_mom: bool
    full_text_preview: str = field(default="")


def build_index(storage_dir: Path) -> list[IndexEntry]:
    entries: list[IndexEntry] = []
    for p in sorted(storage_dir.glob("*.json"), reverse=True):
        if p.name.startswith("."):
            continue
        try:
            with open(p) as f:
                data = json.load(f)
            meta = data.get("metadata", {})
            src = data.get("source", {})
            txn = data.get("transcription", {})
            analysis = data.get("analysis", {})
            created_raw = data.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_raw)
            except (ValueError, TypeError):
                created_at = datetime.min
            full_text = txn.get("full_text", "")
            entries.append(
                IndexEntry(
                    id=data.get("id", p.stem),
                    path=p,
                    created_at=created_at,
                    title=meta.get("title", p.stem),
                    project=meta.get("project", []),
                    participants=meta.get("participants", []),
                    tags=meta.get("tags", []),
                    duration_seconds=src.get("duration_seconds", 0.0),
                    has_mom=bool(analysis.get("mom")),
                    full_text_preview=full_text[:200],
                )
            )
        except Exception:
            continue
    return entries


def filter_transcripts(
    index: list[IndexEntry],
    project: Optional[list[str]] = None,
    participants: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    since: Optional[date] = None,
    until: Optional[date] = None,
    has_mom: Optional[bool] = None,
) -> list[IndexEntry]:
    result = index
    if project:
        lc = [p.lower() for p in project]
        result = [e for e in result if set(lc) & {x.lower() for x in e.project}]
    if participants:
        lc = [p.lower() for p in participants]
        result = [e for e in result if set(lc) & {x.lower() for x in e.participants}]
    if tags:
        lc = [t.lower() for t in tags]
        result = [e for e in result if set(lc) & {x.lower() for x in e.tags}]
    if since:
        result = [e for e in result if e.created_at.date() >= since]
    if until:
        result = [e for e in result if e.created_at.date() <= until]
    if has_mom is not None:
        result = [e for e in result if e.has_mom == has_mom]
    return result


def search_transcripts(
    query: str,
    entries: list[IndexEntry],
    storage_dir: Path,
) -> list[tuple[IndexEntry, list[str]]]:
    query_lower = query.lower()
    results: list[tuple[IndexEntry, list[str]]] = []
    for entry in entries:
        try:
            record: TranscriptRecord = load_transcript(entry.path)
        except Exception:
            continue
        matches = [
            seg.text.strip()
            for seg in record.transcription.segments
            if query_lower in seg.text.lower()
        ]
        if matches:
            results.append((entry, matches))
    return results


def resolve_id(partial_id: str, storage_dir: Path) -> Path:
    """Resolve a full or partial transcript ID to a single Path (error if ambiguous)."""
    candidates = list(storage_dir.glob(f"{partial_id}*.json"))
    if not candidates:
        raise FileNotFoundError(f"No transcript matching '{partial_id}'")
    if len(candidates) > 1:
        ids = ", ".join(p.stem for p in candidates)
        raise ValueError(f"Ambiguous ID '{partial_id}' matches: {ids}")
    return candidates[0]


def resolve_all(partial_id: str, storage_dir: Path) -> list[Path]:
    """Resolve a full or partial transcript ID to all matching Paths."""
    candidates = list(storage_dir.glob(f"{partial_id}*.json"))
    if not candidates:
        raise FileNotFoundError(f"No transcript matching '{partial_id}'")
    return candidates

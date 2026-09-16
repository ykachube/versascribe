"""Shared test fixtures."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    storage = tmp_path / "versascribe"
    storage.mkdir()
    (storage / "audio").mkdir()
    (storage / "tmp").mkdir()
    return storage


@pytest.fixture
def sample_transcript_path() -> Path:
    return FIXTURES_DIR / "sample_transcript.json"


@pytest.fixture
def sample_transcript_record(sample_transcript_path):
    from versascribe.storage.transcript import load_transcript
    return load_transcript(sample_transcript_path)


def make_transcript_file(
    storage: Path,
    *,
    id: str = "20240101_120000_test",
    title: str = "Test Meeting",
    project: list[str] | None = None,
    participants: list[str] | None = None,
    tags: list[str] | None = None,
    created_at: str = "2024-01-01T12:00:00+00:00",
    duration_seconds: float = 300.0,
    full_text: str = "This is a test transcript.",
    has_mom: bool = False,
) -> Path:
    data = {
        "$schema": "versascribe/transcript/v1",
        "id": id,
        "version": 1,
        "created_at": created_at,
        "updated_at": created_at,
        "source": {
            "type": "recording",
            "original_filename": None,
            "audio_file": None,
            "duration_seconds": duration_seconds,
            "audio_device": "BlackHole 2ch",
            "sample_rate": 16000,
            "channels": 1,
        },
        "metadata": {
            "title": title,
            "project": project or [],
            "participants": participants or [],
            "tags": tags or [],
            "language": "en",
            "whisper_model": "base",
        },
        "transcription": {
            "engine": "faster-whisper",
            "model_size": "base",
            "language_detected": "en",
            "language_probability": 0.99,
            "segments": [
                {"id": 0, "start": 0.0, "end": 5.0, "text": full_text, "words": None}
            ],
            "full_text": full_text,
        },
        "analysis": {
            "mom": {
                "generated_at": "2024-01-01T12:30:00+00:00",
                "model": "claude-sonnet-5",
                "content": {
                    "meeting_title": title,
                    "date": "2024-01-01",
                    "duration_minutes": 5,
                    "attendees": participants or [],
                    "agenda": [],
                    "discussion_points": [],
                    "decisions": [],
                    "action_items": [],
                    "next_meeting": None,
                    "notes": None,
                },
            }
            if has_mom
            else None,
        },
    }
    path = storage / f"{id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def populated_storage(tmp_storage: Path) -> Path:
    make_transcript_file(
        tmp_storage,
        id="20240101_120000_standup",
        title="Daily Standup",
        project=["backend"],
        participants=["Alice", "Bob"],
        tags=["standup"],
        created_at="2024-01-01T12:00:00+00:00",
        full_text="We discussed the API latency issue.",
    )
    make_transcript_file(
        tmp_storage,
        id="20240108_100000_planning",
        title="Sprint Planning",
        project=["backend", "frontend"],
        participants=["Alice", "Carol"],
        tags=["planning"],
        created_at="2024-01-08T10:00:00+00:00",
        full_text="Planning sprint tasks and assigning owners.",
        has_mom=True,
    )
    make_transcript_file(
        tmp_storage,
        id="20240115_140000_retro",
        title="Sprint Retrospective",
        project=["backend"],
        participants=["Bob", "Carol"],
        tags=["retro"],
        created_at="2024-01-15T14:00:00+00:00",
        full_text="What went well, what could be improved.",
    )
    return tmp_storage

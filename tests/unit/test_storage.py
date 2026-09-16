"""Unit tests for storage/transcript.py and storage/paths.py."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from versascribe.storage.paths import make_slug, new_audio_path, new_transcript_path
from versascribe.storage.transcript import (
    AnalysisBlock,
    SourceInfo,
    TranscriptMetadata,
    TranscriptRecord,
    TranscriptionData,
    TranscriptSegment,
    load_transcript,
    save_transcript,
)


def _make_minimal_record(id: str = "20240101_120000_test") -> TranscriptRecord:
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return TranscriptRecord(
        **{
            "$schema": "versascribe/transcript/v1",
            "id": id,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "source": SourceInfo(type="recording", duration_seconds=60.0),
            "metadata": TranscriptMetadata(title="Test Meeting"),
            "transcription": TranscriptionData(
                model_size="base",
                language_detected="en",
                language_probability=0.99,
                segments=[
                    TranscriptSegment(id=0, start=0.0, end=5.0, text="Hello world.")
                ],
                full_text="Hello world.",
            ),
            "analysis": AnalysisBlock(),
        }
    )


class TestTranscriptRoundtrip:
    def test_save_and_load(self, tmp_path: Path) -> None:
        record = _make_minimal_record()
        path = tmp_path / "test.json"
        save_transcript(record, path)
        loaded = load_transcript(path)
        assert loaded.id == record.id
        assert loaded.metadata.title == "Test Meeting"
        assert loaded.transcription.full_text == "Hello world."

    def test_save_uses_schema_alias(self, tmp_path: Path) -> None:
        record = _make_minimal_record()
        path = tmp_path / "test.json"
        save_transcript(record, path)
        data = json.loads(path.read_text())
        assert "$schema" in data
        assert data["$schema"] == "versascribe/transcript/v1"

    def test_atomic_write(self, tmp_path: Path) -> None:
        record = _make_minimal_record()
        path = tmp_path / "test.json"
        save_transcript(record, path)
        assert path.exists()
        assert not (tmp_path / "test.tmp").exists()

    def test_load_sample_fixture(self, sample_transcript_record) -> None:
        r = sample_transcript_record
        assert r.id == "20240315_143022_team-standup"
        assert r.metadata.title == "Team Standup"
        assert len(r.transcription.segments) == 3
        assert r.metadata.participants == ["Alice", "Bob", "Carol"]


class TestMakeSlug:
    def test_basic(self) -> None:
        assert make_slug("Team Standup") == "team-standup"

    def test_special_chars(self) -> None:
        assert make_slug("Q1 Planning!") == "q1-planning"

    def test_long_title_truncated(self) -> None:
        long = "A" * 100
        assert len(make_slug(long)) <= 40

    def test_empty_becomes_untitled(self) -> None:
        assert make_slug("") == "untitled"
        assert make_slug("!!!") == "untitled"


class TestNewPaths:
    def test_transcript_path_format(self, tmp_path: Path) -> None:
        ts = datetime(2024, 3, 15, 14, 30, 22, tzinfo=timezone.utc)
        p = new_transcript_path(tmp_path, "Team Standup", ts)
        assert p.name == "20240315_143022_team-standup.json"
        assert p.parent == tmp_path

    def test_audio_path_format(self, tmp_path: Path) -> None:
        ts = datetime(2024, 3, 15, 14, 30, 22, tzinfo=timezone.utc)
        p = new_audio_path(tmp_path, "Team Standup", ts)
        assert p.name == "20240315_143022_team-standup.wav"

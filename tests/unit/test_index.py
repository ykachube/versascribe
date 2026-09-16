"""Unit tests for storage/index.py."""

from __future__ import annotations

from datetime import date

import pytest

from versascribe.storage.index import (
    IndexEntry,
    build_index,
    filter_transcripts,
    resolve_id,
    search_transcripts,
)


class TestBuildIndex:
    def test_returns_all_entries(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        assert len(entries) == 3

    def test_sorted_newest_first(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        dates = [e.created_at for e in entries]
        assert dates == sorted(dates, reverse=True)

    def test_entry_fields(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        standup = next(e for e in entries if "standup" in e.id.lower())
        assert standup.title == "Daily Standup"
        assert "backend" in standup.project
        assert "Alice" in standup.participants
        assert not standup.has_mom

    def test_has_mom_detected(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        planning = next(e for e in entries if "planning" in e.id.lower())
        assert planning.has_mom

    def test_ignores_dotfiles(self, populated_storage) -> None:
        (populated_storage / ".index_cache.json").write_text('{"x": 1}')
        entries = build_index(populated_storage)
        assert len(entries) == 3

    def test_empty_dir(self, tmp_storage) -> None:
        assert build_index(tmp_storage) == []


class TestFilterTranscripts:
    def test_no_filters_returns_all(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        assert filter_transcripts(entries) == entries

    def test_filter_by_project(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, project=["frontend"])
        assert len(result) == 1
        assert result[0].title == "Sprint Planning"

    def test_filter_by_participant(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, participants=["Carol"])
        ids = [e.id for e in result]
        assert any("planning" in i for i in ids)
        assert any("retro" in i for i in ids)

    def test_filter_case_insensitive(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, participants=["alice"])
        assert len(result) == 2

    def test_filter_by_tag(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, tags=["retro"])
        assert len(result) == 1

    def test_filter_since(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, since=date(2024, 1, 8))
        assert len(result) == 2

    def test_filter_until(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, until=date(2024, 1, 1))
        assert len(result) == 1

    def test_filter_has_mom_true(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, has_mom=True)
        assert len(result) == 1
        assert result[0].title == "Sprint Planning"

    def test_filter_has_mom_false(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        result = filter_transcripts(entries, has_mom=False)
        assert len(result) == 2


class TestSearchTranscripts:
    def test_finds_match(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        results = search_transcripts("latency", entries, populated_storage)
        assert len(results) == 1
        assert results[0][0].title == "Daily Standup"

    def test_case_insensitive(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        results = search_transcripts("LATENCY", entries, populated_storage)
        assert len(results) == 1

    def test_no_match(self, populated_storage) -> None:
        entries = build_index(populated_storage)
        results = search_transcripts("xyznonexistent", entries, populated_storage)
        assert results == []


class TestResolveId:
    def test_full_id(self, populated_storage) -> None:
        p = resolve_id("20240101_120000_standup", populated_storage)
        assert p.exists()

    def test_prefix(self, populated_storage) -> None:
        p = resolve_id("20240101", populated_storage)
        assert p.exists()

    def test_not_found(self, populated_storage) -> None:
        with pytest.raises(FileNotFoundError):
            resolve_id("nonexistent_id", populated_storage)

    def test_ambiguous(self, populated_storage) -> None:
        with pytest.raises(ValueError):
            resolve_id("2024", populated_storage)

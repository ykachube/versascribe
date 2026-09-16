"""Unit tests for AI MoM prompt building and JSON extraction."""

from __future__ import annotations

import json

import pytest

from versascribe.ai.mom import _extract_json, build_mom_user_prompt
from versascribe.storage.transcript import MomContent


class TestBuildMomPrompt:
    def test_contains_title(self, sample_transcript_record) -> None:
        prompt = build_mom_user_prompt(sample_transcript_record)
        assert "Team Standup" in prompt

    def test_contains_participants(self, sample_transcript_record) -> None:
        prompt = build_mom_user_prompt(sample_transcript_record)
        assert "Alice" in prompt
        assert "Bob" in prompt

    def test_contains_timestamps(self, sample_transcript_record) -> None:
        prompt = build_mom_user_prompt(sample_transcript_record)
        assert "[00:00]" in prompt

    def test_contains_json_schema(self, sample_transcript_record) -> None:
        prompt = build_mom_user_prompt(sample_transcript_record)
        assert "action_items" in prompt
        assert "discussion_points" in prompt


class TestExtractJson:
    def test_plain_json(self) -> None:
        text = '{"key": "value"}'
        assert _extract_json(text) == '{"key": "value"}'

    def test_strips_markdown_fences(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        extracted = _extract_json(text)
        assert extracted == '{"key": "value"}'

    def test_json_with_surrounding_text(self) -> None:
        text = 'Here is the result:\n{"meeting_title": "Test"}\nDone.'
        extracted = _extract_json(text)
        data = json.loads(extracted)
        assert data["meeting_title"] == "Test"


class TestMomContent:
    def test_validate_minimal(self) -> None:
        data = {
            "meeting_title": "Test",
            "date": "2024-01-01",
            "attendees": [],
            "agenda": [],
            "discussion_points": [],
            "decisions": [],
            "action_items": [],
        }
        mom = MomContent.model_validate(data)
        assert mom.meeting_title == "Test"

    def test_action_item_nullable_owner(self) -> None:
        data = {
            "meeting_title": "Test",
            "date": "2024-01-01",
            "action_items": [{"owner": None, "task": "Write tests", "due_date": None}],
        }
        mom = MomContent.model_validate(data)
        assert mom.action_items[0].owner is None

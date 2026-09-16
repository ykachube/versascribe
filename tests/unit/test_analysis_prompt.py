"""Unit tests for AI trend analysis prompt building."""

from __future__ import annotations

from versascribe.ai.analysis import build_analysis_user_prompt
from versascribe.storage.transcript import load_transcript
from pathlib import Path


FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_sample():
    return load_transcript(FIXTURES / "sample_transcript.json")


class TestBuildAnalysisPrompt:
    def test_contains_all_titles(self) -> None:
        r1 = _load_sample()
        r2 = _load_sample()
        r2.metadata.title = "Other Meeting"
        prompt = build_analysis_user_prompt([r1, r2], focus=None)
        assert "Team Standup" in prompt
        assert "Other Meeting" in prompt

    def test_meeting_count_in_prompt(self) -> None:
        r = _load_sample()
        prompt = build_analysis_user_prompt([r, r, r], focus=None)
        assert "3 meeting" in prompt

    def test_focus_clause_included(self) -> None:
        r = _load_sample()
        prompt = build_analysis_user_prompt([r], focus="action items with no owner")
        assert "action items with no owner" in prompt

    def test_no_focus_no_clause(self) -> None:
        r = _load_sample()
        prompt = build_analysis_user_prompt([r], focus=None)
        assert "Focus your analysis" not in prompt

    def test_long_transcript_truncated(self) -> None:
        r = _load_sample()
        r.transcription.full_text = "A" * 5000
        prompt = build_analysis_user_prompt([r], focus=None)
        assert "...[truncated]" in prompt

    def test_short_transcript_not_truncated(self) -> None:
        r = _load_sample()
        r.transcription.full_text = "Short text."
        prompt = build_analysis_user_prompt([r], focus=None)
        assert "...[truncated]" not in prompt

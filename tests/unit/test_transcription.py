"""Unit tests for transcription/whisper.py."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from versascribe.transcription.whisper import get_model, transcribe_audio


@dataclass
class FakeSegment:
    id: int = 0
    start: float = 0.0
    end: float = 5.0
    text: str = " Hello world."
    avg_logprob: float = -0.2
    compression_ratio: float = 1.1
    no_speech_prob: float = 0.01
    words: Optional[list] = None


@dataclass
class FakeInfo:
    language: str = "en"
    language_probability: float = 0.99


class TestGetModel:
    def test_model_cached(self) -> None:
        import versascribe.transcription.whisper as w
        mock_model = MagicMock()
        with patch("faster_whisper.WhisperModel", return_value=mock_model):
            w._model_cache.clear()
            m1 = get_model("tiny")
            m2 = get_model("tiny")
            assert m1 is m2

    def test_different_sizes_separate_entries(self) -> None:
        import versascribe.transcription.whisper as w
        mock_a = MagicMock()
        mock_b = MagicMock()
        with patch("faster_whisper.WhisperModel", side_effect=[mock_a, mock_b]):
            w._model_cache.clear()
            get_model("tiny")
            get_model("base")
            assert "tiny" in w._model_cache
            assert "base" in w._model_cache


class TestTranscribeAudio:
    def _make_mock_model(self):
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([FakeSegment()], FakeInfo())
        return mock_model

    def test_returns_transcription_result(self, tmp_path: Path) -> None:
        import versascribe.transcription.whisper as w
        mock_model = self._make_mock_model()
        w._model_cache["base"] = mock_model
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"")
        result = transcribe_audio(audio, model_size="base")
        assert result.language_detected == "en"
        assert len(result.segments) == 1
        assert "Hello" in result.full_text

    def test_full_text_joined(self, tmp_path: Path) -> None:
        import versascribe.transcription.whisper as w
        seg1 = FakeSegment(text=" Hello")
        seg2 = FakeSegment(id=1, text=" world.")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([seg1, seg2], FakeInfo())
        w._model_cache["base"] = mock_model
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"")
        result = transcribe_audio(audio, model_size="base")
        assert result.full_text == "Hello world."

    def test_word_timestamps_none_when_disabled(self, tmp_path: Path) -> None:
        import versascribe.transcription.whisper as w
        mock_model = self._make_mock_model()
        w._model_cache["base"] = mock_model
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"")
        result = transcribe_audio(audio, model_size="base", word_timestamps=False)
        assert result.segments[0].words is None

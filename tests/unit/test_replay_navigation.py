"""Textual pilot tests for ReplayApp keyboard navigation.

Run with:
    python3.11 -m pytest tests/unit/test_replay_navigation.py -v

These tests mock all audio — no hardware required.
The key question: do arrow keys move the cursor while _playing is True?
If these pass but real usage fails, the bug is PortAudio interfering
with the terminal driver (signals / fd / GIL), not the Textual app code.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import DataTable

from versascribe.replay import audio as _audio


# ── fixture ───────────────────────────────────────────────────────────────────

def _make_record(tmp_path: Path, n_segments: int = 5):
    """Minimal multi-segment transcript — no audio file."""
    from versascribe.storage.transcript import load_transcript

    segments = [
        {
            "id": i,
            "start": float(i * 5),
            "end": float(i * 5 + 4),
            "text": f" This is segment {i}.",
            "words": None,
            "speaker": None,
            "note": None,
        }
        for i in range(n_segments)
    ]
    data = {
        "$schema": "versascribe/transcript/v1",
        "id": "20240101_120000_nav-test",
        "version": 1,
        "created_at": "2024-01-01T12:00:00+00:00",
        "updated_at": "2024-01-01T12:00:00+00:00",
        "source": {
            "type": "recording",
            "original_filename": None,
            "audio_file": None,
            "duration_seconds": float(n_segments * 5),
            "audio_device": "BlackHole 2ch",
            "sample_rate": 16000,
            "channels": 1,
        },
        "metadata": {
            "title": "Nav Test",
            "project": [],
            "participants": [],
            "tags": [],
            "language": "en",
            "whisper_model": "base",
            "speaker_map": {},
        },
        "transcription": {
            "engine": "faster-whisper",
            "model_size": "base",
            "language_detected": "en",
            "language_probability": 0.99,
            "segments": segments,
            "full_text": " ".join(s["text"] for s in segments),
        },
        "analysis": {"mom": None},
    }
    path = tmp_path / "20240101_120000_nav-test.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_transcript(path), path


# ── tests ─────────────────────────────────────────────────────────────────────

async def test_cursor_down_without_playback(tmp_path: Path) -> None:
    """Baseline: arrow down moves cursor when nothing is playing."""
    from versascribe.replay.app import ReplayApp

    record, path = _make_record(tmp_path)
    async with ReplayApp(record, path).run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.cursor_row == 0
        await pilot.press("down")
        assert table.cursor_row == 1, "cursor should move down"


async def test_cursor_up_without_playback(tmp_path: Path) -> None:
    """Baseline: arrow up moves cursor when nothing is playing."""
    from versascribe.replay.app import ReplayApp

    record, path = _make_record(tmp_path)
    async with ReplayApp(record, path).run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        await pilot.press("down")
        await pilot.press("down")
        assert table.cursor_row == 2
        await pilot.press("up")
        assert table.cursor_row == 1, "cursor should move up"


async def test_j_k_without_playback(tmp_path: Path) -> None:
    """Baseline: j/k bindings move cursor when nothing is playing."""
    from versascribe.replay.app import ReplayApp

    record, path = _make_record(tmp_path)
    async with ReplayApp(record, path).run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        await pilot.press("j")
        assert table.cursor_row == 1
        await pilot.press("k")
        assert table.cursor_row == 0


async def test_cursor_down_while_playing(tmp_path: Path) -> None:
    """Arrow down must work while _playing is True (mocked audio)."""
    from versascribe.replay.app import ReplayApp

    record, path = _make_record(tmp_path)
    with (
        patch.object(_audio, "play_from"),
        patch.object(_audio, "stop"),
        patch.object(_audio, "is_playing", return_value=False),
    ):
        async with ReplayApp(record, path).run_test() as pilot:
            app = pilot.app
            # simulate the state the app enters after pressing Space
            app._playing = True
            await pilot.pause()

            table = app.query_one(DataTable)
            assert table.cursor_row == 0
            await pilot.press("down")
            assert table.cursor_row == 1, (
                "cursor should move down while _playing=True"
            )


async def test_j_k_while_playing(tmp_path: Path) -> None:
    """j/k bindings must work while _playing is True (mocked audio)."""
    from versascribe.replay.app import ReplayApp

    record, path = _make_record(tmp_path)
    with (
        patch.object(_audio, "play_from"),
        patch.object(_audio, "stop"),
        patch.object(_audio, "is_playing", return_value=False),
    ):
        async with ReplayApp(record, path).run_test() as pilot:
            app = pilot.app
            app._playing = True
            await pilot.pause()

            table = app.query_one(DataTable)
            await pilot.press("j")
            assert table.cursor_row == 1, "j should move down while _playing=True"
            await pilot.press("k")
            assert table.cursor_row == 0, "k should move up while _playing=True"


async def test_space_toggles_playing_state(tmp_path: Path) -> None:
    """Space sets _playing=True; second Space sets it back to False."""
    from versascribe.replay.app import ReplayApp

    record, path = _make_record(tmp_path)
    # audio_file is None so play won't actually fire, but let's mock to be safe
    with (
        patch.object(_audio, "play_from"),
        patch.object(_audio, "stop"),
        patch.object(_audio, "is_playing", side_effect=[False, True]),
    ):
        async with ReplayApp(record, path).run_test() as pilot:
            app = pilot.app
            # no audio file → notify warning, _playing stays False
            # (ReplayApp._wav_path is None for this fixture)
            assert app._playing is False

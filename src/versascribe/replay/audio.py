"""Background audio playback for replay mode.

Uses a child process (ffplay or afplay) instead of sounddevice/PortAudio.
Running audio in a separate process eliminates GIL contention and avoids
CoreAudio occupying the main thread's run loop, both of which blocked
Textual's event loop and made keyboard navigation unresponsive.

Player precedence (first available wins):
  1. ffplay  — supports -ss seek offset (brew install ffmpeg)
  2. afplay  — macOS built-in, no seek support

Diagnostic log (opt-in):
  vs replay <id> --debug-audio
  tail -f ~/.versascribe/audio_debug.log
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

_lock = threading.Lock()
_proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]

_log = logging.getLogger("versascribe.replay.audio")


def configure_log(storage_dir: Path) -> None:
    """Call once at replay startup to enable the debug log file."""
    log_path = storage_dir / "audio_debug.log"
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _log.addHandler(handler)
    _log.setLevel(logging.DEBUG)
    _log.info("audio logger configured → %s", log_path)


def play_from(
    wav_path: Path,
    start_seconds: float,
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    """Start playback from start_seconds. Stops any current playback first."""
    stop()

    cmd = _player_command(wav_path, start_seconds)
    if cmd is None:
        _log.warning("no audio player found; install ffmpeg (brew install ffmpeg) for playback")
        return

    _log.info("launching: %s", " ".join(str(c) for c in cmd))

    def _worker() -> None:
        global _proc
        proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with _lock:
                _proc = proc
            proc.wait()
            _log.info("playback finished (pid=%d rc=%d)", proc.pid, proc.returncode)
        except Exception as exc:
            _log.exception("playback error: %s", exc)
        finally:
            with _lock:
                if _proc is proc:
                    _proc = None
            if on_done:
                on_done()

    threading.Thread(target=_worker, daemon=True, name="audio-worker").start()


def stop() -> None:
    """Terminate the audio child process if running."""
    global _proc
    with _lock:
        proc = _proc
        _proc = None
    if proc and proc.poll() is None:
        _log.info("stop(): terminating pid=%d", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            _log.warning("process did not exit after 2s, killing")
            proc.kill()


def is_playing() -> bool:
    with _lock:
        return _proc is not None and _proc.poll() is None


def _player_command(wav_path: Path, start_seconds: float) -> Optional[list[str]]:
    if shutil.which("ffplay"):
        return [
            "ffplay",
            "-ss", str(start_seconds),
            "-i", str(wav_path),
            "-nodisp",
            "-autoexit",
            "-loglevel", "quiet",
        ]
    if shutil.which("afplay"):
        if start_seconds > 0.5:
            _log.warning(
                "afplay does not support seeking; playback starts from 0:00 "
                "(install ffmpeg for seek support: brew install ffmpeg)"
            )
        return ["afplay", str(wav_path)]
    return None

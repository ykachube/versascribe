"""Filesystem path resolution and filename generation."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from versascribe.config import AppConfig


def get_storage_dir(config: "AppConfig") -> Path:
    d = Path(config.storage_path).expanduser().resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_audio_dir(config: "AppConfig") -> Path:
    d = get_storage_dir(config) / "audio"
    d.mkdir(exist_ok=True)
    return d


def get_tmp_dir(config: "AppConfig") -> Path:
    d = get_storage_dir(config) / "tmp"
    d.mkdir(exist_ok=True)
    return d


def make_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:40] or "untitled"


def _ts_prefix(ts: datetime) -> str:
    return ts.strftime("%Y%m%d_%H%M%S")


def new_transcript_path(storage_dir: Path, title: str, ts: datetime) -> Path:
    slug = make_slug(title)
    return storage_dir / f"{_ts_prefix(ts)}_{slug}.json"


def new_audio_path(audio_dir: Path, title: str, ts: datetime) -> Path:
    slug = make_slug(title)
    return audio_dir / f"{_ts_prefix(ts)}_{slug}.wav"


def new_tmp_wav_path(tmp_dir: Path, stem: str, ts: datetime) -> Path:
    slug = make_slug(stem)
    return tmp_dir / f"{_ts_prefix(ts)}_{slug}_extracted.wav"

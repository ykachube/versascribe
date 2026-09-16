"""Unit tests for config.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from versascribe.config import AppConfig, load_config, save_config


class TestAppConfig:
    def test_defaults(self) -> None:
        cfg = AppConfig()
        assert cfg.whisper_model == "base"
        assert cfg.blackhole_device == "BlackHole 2ch"
        assert cfg.claude_api_key is None
        assert cfg.word_timestamps is False

    def test_storage_dir_expands_tilde(self, tmp_path: Path) -> None:
        cfg = AppConfig(storage_path=str(tmp_path))
        assert cfg.storage_dir == tmp_path.resolve()


class TestLoadSaveConfig:
    def test_returns_defaults_when_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "versascribe.config.CONFIG_PATH", tmp_path / "nonexistent.json"
        )
        cfg = load_config()
        assert cfg.whisper_model == "base"

    def test_roundtrip(self, tmp_path: Path, monkeypatch) -> None:
        config_path = tmp_path / "config.json"
        monkeypatch.setattr("versascribe.config.CONFIG_PATH", config_path)
        cfg = AppConfig(whisper_model="small", claude_api_key="sk-test")
        save_config(cfg)
        loaded = load_config()
        assert loaded.whisper_model == "small"
        assert loaded.claude_api_key == "sk-test"

    def test_save_creates_parent_dirs(self, tmp_path: Path, monkeypatch) -> None:
        config_path = tmp_path / "nested" / "config.json"
        monkeypatch.setattr("versascribe.config.CONFIG_PATH", config_path)
        save_config(AppConfig())
        assert config_path.exists()

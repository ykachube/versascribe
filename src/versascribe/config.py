"""Application configuration: load, save, and defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict

CONFIG_PATH = Path("~/.versascribe/config.json").expanduser()

VALID_KEYS = {
    "claude_api_key",
    "claude_model",
    "whisper_model",
    "blackhole_device",
    "storage_path",
    "word_timestamps",
    "hf_token",
    "diarize_by_default",
}


class AppConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    claude_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-5"
    whisper_model: str = "base"
    blackhole_device: str = "BlackHole 2ch"
    storage_path: str = "~/.versascribe"
    word_timestamps: bool = False
    hf_token: Optional[str] = None
    diarize_by_default: bool = False

    @property
    def storage_dir(self) -> Path:
        return Path(self.storage_path).expanduser().resolve()


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig()
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return AppConfig.model_validate(data)
    except Exception:
        return AppConfig()


def save_config(config: AppConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(config.model_dump(exclude_none=False), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(CONFIG_PATH)

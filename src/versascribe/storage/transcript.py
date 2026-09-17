"""Pydantic models for transcript records and CRUD helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class WordTimestamp(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    word: str
    start: float
    end: float
    probability: float


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    note: Optional[str] = None
    avg_logprob: Optional[float] = None
    compression_ratio: Optional[float] = None
    no_speech_prob: Optional[float] = None
    words: Optional[list[WordTimestamp]] = None


class TranscriptionData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    engine: str = "faster-whisper"
    model_size: str
    language_detected: str
    language_probability: float
    segments: list[TranscriptSegment]
    full_text: str


class SourceInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["recording", "import"]
    original_filename: Optional[str] = None
    audio_file: Optional[str] = None
    duration_seconds: float = 0.0
    audio_device: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1


class TranscriptMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    project: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: Optional[str] = None
    whisper_model: Optional[str] = None
    speaker_map: dict[str, str] = Field(default_factory=dict)


class ActionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    owner: Optional[str] = None
    task: str
    due_date: Optional[str] = None


class DiscussionPoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    topic: str
    summary: str


class MomContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    meeting_title: str
    date: str
    duration_minutes: Optional[float] = None
    attendees: list[str] = Field(default_factory=list)
    agenda: list[str] = Field(default_factory=list)
    discussion_points: list[DiscussionPoint] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    next_meeting: Optional[str] = None
    notes: Optional[str] = None


class MomRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    generated_at: str
    model: str
    content: MomContent


class AnalysisBlock(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mom: Optional[MomRecord] = None


class TranscriptRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_: str = Field("versascribe/transcript/v1", alias="$schema")
    id: str
    version: int = 1
    created_at: datetime
    updated_at: datetime
    source: SourceInfo
    metadata: TranscriptMetadata
    transcription: TranscriptionData
    analysis: AnalysisBlock = Field(default_factory=AnalysisBlock)

    def model_dump_for_save(self) -> dict:
        d = self.model_dump(by_alias=True, mode="json")
        return d


def load_transcript(path: Path) -> TranscriptRecord:
    with open(path) as f:
        data = json.load(f)
    return TranscriptRecord.model_validate(data)


def save_transcript(record: TranscriptRecord, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(record.model_dump_for_save(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def list_transcript_paths(storage_dir: Path) -> Iterator[Path]:
    yield from sorted(storage_dir.glob("*.json"), reverse=True)

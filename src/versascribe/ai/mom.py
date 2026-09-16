"""MoM generation via Claude."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from versascribe.storage.transcript import MomContent, MomRecord

if TYPE_CHECKING:
    import anthropic
    from versascribe.storage.transcript import TranscriptRecord

_SYSTEM_PROMPT = (
    "You are an expert meeting secretary. Given a meeting transcript with timestamps, "
    "produce structured Minutes of Meeting as JSON. Be concise and factual. "
    "Extract only information explicitly stated in the transcript. "
    "For fields that cannot be determined from the transcript, use null. "
    "Output only valid JSON, no markdown fences, no explanation."
)

_OUTPUT_SCHEMA = {
    "meeting_title": "string",
    "date": "YYYY-MM-DD",
    "duration_minutes": "number or null",
    "attendees": ["string"],
    "agenda": ["string or null if not stated"],
    "discussion_points": [{"topic": "string", "summary": "string"}],
    "decisions": ["string"],
    "action_items": [{"owner": "string|null", "task": "string", "due_date": "YYYY-MM-DD|null"}],
    "next_meeting": "ISO datetime string or null",
    "notes": "string or null",
}

_MAX_TEXT_CHARS = 80_000


def build_mom_user_prompt(record: "TranscriptRecord") -> str:
    lines = [
        f"Meeting Title: {record.metadata.title or 'Unknown'}",
        f"Date: {record.created_at.strftime('%Y-%m-%d %H:%M')}",
        f"Duration: {record.source.duration_seconds / 60:.1f} minutes",
        f"Known participants: {', '.join(record.metadata.participants) or 'Not specified'}",
        f"Project tags: {', '.join(record.metadata.project) or 'None'}",
        "",
        "TRANSCRIPT:",
    ]

    total_chars = 0
    truncated = False
    for seg in record.transcription.segments:
        m, s = divmod(int(seg.start), 60)
        line = f"[{m:02d}:{s:02d}] {seg.text.strip()}"
        total_chars += len(line)
        if total_chars > _MAX_TEXT_CHARS:
            truncated = True
            break
        lines.append(line)

    if truncated:
        lines.append("[...transcript truncated due to length...]")

    lines += [
        "",
        "Produce Minutes of Meeting as JSON with this exact structure:",
        json.dumps(_OUTPUT_SCHEMA, indent=2),
    ]
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0)
    return text


def generate_mom(
    client: "anthropic.Anthropic",
    record: "TranscriptRecord",
    model: str,
) -> MomRecord:
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_mom_user_prompt(record)}],
    )
    raw = response.content[0].text
    data = json.loads(_extract_json(raw))
    content = MomContent.model_validate(data)
    return MomRecord(
        generated_at=datetime.now(timezone.utc).isoformat(),
        model=model,
        content=content,
    )

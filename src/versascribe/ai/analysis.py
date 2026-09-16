"""Trend analysis across multiple transcripts via Claude."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import anthropic
    from versascribe.storage.transcript import TranscriptRecord

_SYSTEM_PROMPT = (
    "You are an expert organizational analyst. "
    "Given summaries of multiple meeting transcripts, identify patterns, "
    "recurring themes, action item trends, and provide actionable insights. "
    "Output only valid JSON, no markdown fences, no explanation."
)

_OUTPUT_SCHEMA = {
    "period": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"},
    "meeting_count": "number",
    "recurring_topics": [
        {"topic": "string", "frequency": "int", "trend": "increasing|decreasing|stable"}
    ],
    "key_decisions": ["string"],
    "open_action_items": [
        {"task": "string", "owner": "string|null", "first_mentioned": "YYYY-MM-DD"}
    ],
    "participant_engagement": [{"participant": "string", "summary": "string"}],
    "risks_and_concerns": ["string"],
    "recommendations": ["string"],
    "summary": "One paragraph executive summary",
}

_MAX_PREVIEW_CHARS = 1500


def build_analysis_user_prompt(
    transcripts: list["TranscriptRecord"],
    focus: Optional[str],
) -> str:
    summaries = []
    for t in transcripts:
        preview = t.transcription.full_text[:_MAX_PREVIEW_CHARS]
        if len(t.transcription.full_text) > _MAX_PREVIEW_CHARS:
            preview += " ...[truncated]"
        summaries.append(
            f"=== {t.metadata.title} | {t.created_at.date()} | "
            f"{t.source.duration_seconds / 60:.0f}min | "
            f"Participants: {', '.join(t.metadata.participants) or 'unknown'} ===\n"
            + preview
        )

    focus_clause = f"\nFocus your analysis specifically on: {focus}\n" if focus else ""

    return (
        f"Analyze these {len(transcripts)} meeting transcripts:{focus_clause}\n\n"
        + "\n\n".join(summaries)
        + f"\n\nProduce analysis as JSON:\n{json.dumps(_OUTPUT_SCHEMA, indent=2)}"
    )


def _extract_json(text: str) -> str:
    import re
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def generate_analysis(
    client: "anthropic.Anthropic",
    transcripts: list["TranscriptRecord"],
    focus: Optional[str],
    model: str,
) -> dict:
    prompt = build_analysis_user_prompt(transcripts, focus)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    return json.loads(_extract_json(raw))

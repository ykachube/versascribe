# Claude Integration

VersaScribe uses the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) to power two AI features: **Minutes of Meeting (MoM)** generation and **cross-meeting trend analysis**. Both are entirely optional — all other commands work without any API key.

---

## Setup

```bash
vs config --set claude_api_key=sk-ant-api03-...
```

The key is stored in `~/.versascribe/config.json`. VersaScribe uses it only when you explicitly run `vs mom` or `vs analyze`.

### Model selection

The default model is `claude-sonnet-5`. You can change it globally or per-command:

```bash
# Change default
vs config --set claude_model=claude-opus-4-8

# Override for one call
vs mom <id> --model claude-opus-4-8
vs analyze --project backend --model claude-sonnet-5
```

---

## Minutes of Meeting (`vs mom`)

### What it does

Given a transcript, Claude produces a structured MoM with:

- Meeting title, date, duration
- Attendees
- Agenda (if stated)
- Discussion points (topic + summary)
- Decisions made
- Action items (task, owner, due date)
- Next meeting date/time
- Notes

### How it works

1. The full timestamped transcript is formatted as `[MM:SS] segment text`
2. Known metadata (title, participants, project, duration) is prepended as context
3. Claude is instructed to output **only valid JSON** matching the MoM schema
4. The result is validated with Pydantic and cached in the transcript's JSON under `analysis.mom`

Long meetings (>3 hours) are truncated to approximately 80,000 characters before sending.

### Caching

MoMs are cached inside the transcript file itself. The second time you run `vs mom <id>`, it renders the cached version instantly with no API call. Use `--regenerate` to force a fresh generation.

### System prompt

```
You are an expert meeting secretary. Given a meeting transcript with timestamps,
produce structured Minutes of Meeting as JSON. Be concise and factual.
Extract only information explicitly stated in the transcript.
For fields that cannot be determined from the transcript, use null.
Output only valid JSON, no markdown fences, no explanation.
```

### Output schema

```json
{
  "meeting_title": "string",
  "date": "YYYY-MM-DD",
  "duration_minutes": "number | null",
  "attendees": ["string"],
  "agenda": ["string"],
  "discussion_points": [{ "topic": "string", "summary": "string" }],
  "decisions": ["string"],
  "action_items": [{ "owner": "string | null", "task": "string", "due_date": "YYYY-MM-DD | null" }],
  "next_meeting": "ISO datetime | null",
  "notes": "string | null"
}
```

### Token usage estimate

| Meeting length | Approximate input tokens | Approximate cost (Sonnet 5) |
|---|---|---|
| 30 min | ~3,000 | ~$0.01 |
| 1 hour | ~6,000 | ~$0.02 |
| 2 hours | ~12,000 | ~$0.04 |
| 3 hours | ~18,000 | ~$0.05 |

---

## Trend Analysis (`vs analyze`)

### What it does

Analyzes a set of transcripts (filtered by project, participant, date range, or tag) and surfaces:

- Recurring topics with frequency and trend direction (↑ ↓ →)
- Key decisions across the period
- Open action items (mentioned but not resolved)
- Participant engagement summaries
- Risks and concerns
- Recommendations
- Executive summary paragraph

### How it works

1. Matching transcripts are loaded and each is compressed to a ~500-token summary (title, date, duration, participants, first 1,500 characters of transcript text)
2. All summaries are combined into a single prompt
3. Claude is asked to identify patterns across all of them and output a structured JSON analysis
4. The `--focus` flag appends a specific directive to the prompt (e.g., "focus on unresolved blockers")

This approach fits approximately **100 meetings** into a single Claude call within the 200K context window.

### System prompt

```
You are an expert organizational analyst.
Given summaries of multiple meeting transcripts, identify patterns,
recurring themes, action item trends, and provide actionable insights.
Output only valid JSON, no markdown fences, no explanation.
```

### Output schema

```json
{
  "period": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" },
  "meeting_count": "number",
  "recurring_topics": [
    { "topic": "string", "frequency": "int", "trend": "increasing|decreasing|stable" }
  ],
  "key_decisions": ["string"],
  "open_action_items": [
    { "task": "string", "owner": "string | null", "first_mentioned": "YYYY-MM-DD" }
  ],
  "participant_engagement": [{ "participant": "string", "summary": "string" }],
  "risks_and_concerns": ["string"],
  "recommendations": ["string"],
  "summary": "string"
}
```

### Token usage estimate

| Meetings analyzed | Approximate input tokens | Approximate cost (Sonnet 5) |
|---|---|---|
| 10 | ~6,000 | ~$0.02 |
| 25 | ~14,000 | ~$0.04 |
| 50 | ~27,000 | ~$0.08 |
| 100 | ~53,000 | ~$0.15 |

---

## Error handling

If no API key is configured, both commands fail gracefully:

```
╭─ Claude not configured ────────────────────────────────────────────╮
│ Claude API key is not set.                                          │
│                                                                     │
│ Set your API key with:                                              │
│ vs config --set claude_api_key=sk-ant-...                           │
╰─────────────────────────────────────────────────────────────────────╯
```

No other commands are affected by a missing key.

---

## Implementation references

| File | Purpose |
|---|---|
| `src/versascribe/ai/client.py` | Anthropic client factory, `ClaudeNotConfiguredError` guard |
| `src/versascribe/ai/mom.py` | MoM prompt builder, `generate_mom()`, `_extract_json()` |
| `src/versascribe/ai/analysis.py` | Analysis prompt builder, `generate_analysis()` |
| `src/versascribe/commands/mom.py` | `vs mom` command, caching logic |
| `src/versascribe/commands/analyze.py` | `vs analyze` command, filter + batch loading |

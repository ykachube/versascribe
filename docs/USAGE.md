# Usage Guide

## Recording a meeting

Start VersaScribe before or during a meeting. It captures all audio routed through BlackHole.

```bash
# Basic — prompts for title interactively
vs record

# With metadata upfront
vs record --title "Q2 Planning" --project roadmap --participant Alice --participant Bob

# Multiple projects
vs record --title "Cross-team Sync" --project backend --project frontend

# Save audio only, transcribe later
vs record --title "Long Call" --no-transcribe

# Use a specific Whisper model for this session
vs record --title "Board Meeting" --model large-v3

# Force transcription language (skip auto-detection)
vs record --language en

# Enable word-level timestamps
vs record --word-timestamps

# Identify who speaks when (requires diarize extra + HF token — see docs/SETUP.md)
vs record --title "Team Meeting" --diarize
vs record --title "1:1" --diarize --num-speakers 2
```

Press **Ctrl-C** to stop recording. Transcription starts automatically.

---

## Importing a file

Accepts `.mp3`, `.mp4`, `.m4a`, `.mov`, `.mkv`, `.wav`, `.webm`, `.aac`, `.flac`, `.ogg`. Video files are automatically stripped to audio via ffmpeg.

```bash
vs import recording.mp4
vs import zoom_meeting.m4a --title "Client Review" --participant "Sarah" --project acme
vs import interview.mp3 --language en --model small

# With speaker diarization
vs import podcast.mp3 --diarize --num-speakers 3
```

---

## Listing transcripts

```bash
# All transcripts (newest first, up to 50)
vs list

# Filter examples
vs list --project backend
vs list --participant Alice
vs list --tag standup
vs list --since 2024-01-01 --until 2024-03-31
vs list --has-mom                    # only those with a generated MoM
vs list --project backend --since 2024-01-01 --limit 20

# Output formats
vs list --format json                # machine-readable
vs list --format ids                 # just IDs, useful for scripting
```

---

## Viewing a transcript

```bash
# Read the transcript (plain text)
vs show 20240315_143022_team-standup

# With timestamps
vs show 20240315_143022_team-standup --timestamps

# Individual segments with start/end times
vs show 20240315_143022_team-standup --format segments

# Full JSON record
vs show 20240315_143022_team-standup --format json

# Show the MoM (if generated)
vs show 20240315_143022_team-standup --mom
```

You can use a **prefix** of the ID — as long as it's unambiguous:

```bash
vs show 20240315   # works if only one transcript matches that date
```

---

## Searching

```bash
# Full-text search across all transcripts
vs search "API latency"

# With filters
vs search "action item" --project backend --since 2024-01-01

# JSON output (for scripting)
vs search "regression" --format json
```

---

## Tagging and editing metadata

```bash
# Add/remove tags
vs tag 20240315_143022_team-standup --add-tag sprint-15 --remove-tag sprint-14

# Add/remove projects
vs tag 20240315_143022_team-standup --add-project infrastructure

# Add/remove participants
vs tag 20240315_143022_team-standup --add-participant "David"

# Rename the meeting
vs tag 20240315_143022_team-standup --title "Sprint 15 Standup"
```

---

## Generating Minutes of Meeting

Requires a Claude API key: `vs config --set claude_api_key=sk-ant-...`

```bash
# Generate MoM (cached after first run)
vs mom 20240315_143022_team-standup

# Output formats
vs mom 20240315_143022_team-standup --format markdown
vs mom 20240315_143022_team-standup --format json

# Save to a file
vs mom 20240315_143022_team-standup --format markdown --output meeting-notes.md

# Force regeneration (ignores cache)
vs mom 20240315_143022_team-standup --regenerate

# Use a specific Claude model
vs mom 20240315_143022_team-standup --model claude-opus-4-8
```

The MoM includes: title, date, duration, attendees, agenda, discussion points, decisions, action items (with owner + due date), next meeting date.

---

## Trend analysis

Analyzes patterns across multiple transcripts. Requires a Claude API key.

```bash
# Analyze all meetings in a project
vs analyze --project backend

# Analyze meetings by participant
vs analyze --participant Alice

# Date range
vs analyze --since 2024-01-01 --until 2024-03-31

# With a specific focus
vs analyze --project roadmap --focus "recurring blockers and unresolved action items"

# All transcripts
vs analyze --all

# Output formats
vs analyze --project backend --format markdown --output backend-trends.md
vs analyze --project backend --format json

# Lower the minimum count if you have few transcripts
vs analyze --project backend --min-count 1
```

The analysis includes: recurring topics, key decisions, open action items, participant engagement, risks and concerns, recommendations, executive summary.

---

## Configuration

```bash
# List all settings
vs config --list

# Get a single value
vs config --get whisper_model

# Set a value
vs config --set whisper_model=small
vs config --set claude_api_key=sk-ant-...
vs config --set word_timestamps=true
vs config --set storage_path=/custom/path

# Reset a value to its default
vs config --reset whisper_model

# Show the config file path
vs config --show-path
```

### All config keys

| Key | Default | Description |
|---|---|---|
| `claude_api_key` | _(none)_ | Anthropic API key for MoM + analysis |
| `claude_model` | `claude-sonnet-5` | Claude model for AI features |
| `whisper_model` | `base` | Whisper model size (tiny/base/small/medium/large-v3) |
| `blackhole_device` | `BlackHole 2ch` | Audio device name for recording |
| `storage_path` | `~/.versascribe` | Where transcripts and audio are stored |
| `word_timestamps` | `false` | Enable word-level timestamps by default |
| `hf_token` | _(none)_ | HuggingFace token for speaker diarization |
| `diarize_by_default` | `false` | Always run speaker diarization |

---

## Deleting a transcript

```bash
# Interactive confirmation
vs delete 20240315_143022_team-standup

# Skip confirmation
vs delete 20240315_143022_team-standup --yes

# Delete JSON but keep the WAV file
vs delete 20240315_143022_team-standup --keep-audio
```

---

## Scripting examples

```bash
# Export all MoMs for a project as markdown files
for id in $(vs list --project backend --format ids); do
  vs mom "$id" --format markdown --output "moms/${id}.md"
done

# Search and view in one step
vs search "latency" --format ids | head -1 | xargs vs show

# Tag all meetings from a date range
for id in $(vs list --since 2024-01-01 --until 2024-01-31 --format ids); do
  vs tag "$id" --add-tag "q1-2024"
done
```

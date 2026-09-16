"""Rich console helpers, formatters, and live display components."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from versascribe.storage.index import IndexEntry
    from versascribe.storage.transcript import MomContent, TranscriptRecord

console = Console()


def error_panel(message: str, title: str = "Error") -> None:
    console.print(Panel(message, title=f"[bold red]{title}[/bold red]", border_style="red"))


def warn_panel(message: str, title: str = "Warning") -> None:
    console.print(Panel(message, title=f"[bold yellow]{title}[/bold yellow]", border_style="yellow"))


def success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


def render_transcript_table(entries: list["IndexEntry"]) -> None:
    if not entries:
        console.print("[dim]No transcripts found.[/dim]")
        return
    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("ID", style="dim", width=22, no_wrap=True)
    table.add_column("Date", width=12)
    table.add_column("Title", min_width=20)
    table.add_column("Project", width=16)
    table.add_column("Participants", width=20)
    table.add_column("Duration", width=8, justify="right")
    table.add_column("MoM", width=4, justify="center")

    for e in entries:
        date_str = e.created_at.strftime("%Y-%m-%d")
        project_str = ", ".join(e.project) if e.project else ""
        participants_str = ", ".join(e.participants) if e.participants else ""
        duration_str = _fmt_duration(e.duration_seconds) if e.duration_seconds else ""
        mom_str = "[green]✓[/green]" if e.has_mom else ""
        table.add_row(
            e.id[:22],
            date_str,
            e.title,
            project_str,
            participants_str,
            duration_str,
            mom_str,
        )
    console.print(table)


def render_transcript_text(
    record: "TranscriptRecord", timestamps: bool = False
) -> None:
    console.rule(f"[bold]{record.metadata.title}[/bold]")
    meta_parts = []
    if record.metadata.project:
        meta_parts.append(f"Project: {', '.join(record.metadata.project)}")
    if record.metadata.participants:
        meta_parts.append(f"Participants: {', '.join(record.metadata.participants)}")
    meta_parts.append(f"Date: {record.created_at.strftime('%Y-%m-%d %H:%M')}")
    meta_parts.append(f"Duration: {_fmt_duration(record.source.duration_seconds)}")
    console.print("  ".join(meta_parts), style="dim")
    console.print()

    has_speakers = any(s.speaker for s in record.transcription.segments)
    _SPEAKER_COLORS = ["cyan", "magenta", "yellow", "green", "blue", "red"]
    speaker_colors: dict[str, str] = {}

    def _speaker_color(label: str) -> str:
        if label not in speaker_colors:
            speaker_colors[label] = _SPEAKER_COLORS[len(speaker_colors) % len(_SPEAKER_COLORS)]
        return speaker_colors[label]

    prev_speaker: str | None = None
    for seg in record.transcription.segments:
        speaker = seg.speaker
        if has_speakers and speaker and speaker != prev_speaker:
            console.print(f"\n[bold {_speaker_color(speaker)}]{speaker}[/bold {_speaker_color(speaker)}]")
            prev_speaker = speaker
        if timestamps:
            m, s = divmod(int(seg.start), 60)
            ts = f"[dim][{m:02d}:{s:02d}][/dim] "
            console.print(f"{ts}{seg.text.strip()}")
        else:
            console.print(seg.text.strip())


def render_mom(mom: "MomContent", fmt: str = "text") -> None:
    if fmt == "json":
        console.print_json(mom.model_dump_json(indent=2))
        return
    if fmt == "markdown":
        _render_mom_markdown(mom)
        return
    _render_mom_text(mom)


def _render_mom_text(mom: "MomContent") -> None:
    console.rule(f"[bold]Minutes of Meeting — {mom.meeting_title}[/bold]")
    console.print(f"[dim]Date:[/dim] {mom.date}   [dim]Duration:[/dim] {mom.duration_minutes or '?'} min")
    if mom.attendees:
        console.print(f"[dim]Attendees:[/dim] {', '.join(mom.attendees)}")
    console.print()

    if mom.agenda:
        console.print("[bold]Agenda[/bold]")
        for item in mom.agenda:
            console.print(f"  • {item}")
        console.print()

    if mom.discussion_points:
        console.print("[bold]Discussion[/bold]")
        for dp in mom.discussion_points:
            console.print(f"  [bold cyan]{dp.topic}[/bold cyan]")
            console.print(f"  {dp.summary}")
        console.print()

    if mom.decisions:
        console.print("[bold]Decisions[/bold]")
        for d in mom.decisions:
            console.print(f"  • {d}")
        console.print()

    if mom.action_items:
        console.print("[bold]Action Items[/bold]")
        for ai in mom.action_items:
            owner = f"[{ai.owner}]" if ai.owner else ""
            due = f" — due {ai.due_date}" if ai.due_date else ""
            console.print(f"  • {ai.task} {owner}{due}")
        console.print()

    if mom.next_meeting:
        console.print(f"[dim]Next meeting:[/dim] {mom.next_meeting}")
    if mom.notes:
        console.print(f"[dim]Notes:[/dim] {mom.notes}")


def _render_mom_markdown(mom: "MomContent") -> None:
    lines = [
        f"# Minutes of Meeting — {mom.meeting_title}",
        f"**Date:** {mom.date}  **Duration:** {mom.duration_minutes or '?'} min",
        f"**Attendees:** {', '.join(mom.attendees) if mom.attendees else 'N/A'}",
        "",
    ]
    if mom.agenda:
        lines += ["## Agenda"] + [f"- {a}" for a in mom.agenda] + [""]
    if mom.discussion_points:
        lines.append("## Discussion")
        for dp in mom.discussion_points:
            lines += [f"### {dp.topic}", dp.summary, ""]
    if mom.decisions:
        lines += ["## Decisions"] + [f"- {d}" for d in mom.decisions] + [""]
    if mom.action_items:
        lines.append("## Action Items")
        for ai in mom.action_items:
            owner = f" [{ai.owner}]" if ai.owner else ""
            due = f" — due {ai.due_date}" if ai.due_date else ""
            lines.append(f"- {ai.task}{owner}{due}")
        lines.append("")
    if mom.next_meeting:
        lines.append(f"**Next meeting:** {mom.next_meeting}")
    console.print("\n".join(lines))


def render_analysis(data: dict, fmt: str = "text") -> None:
    if fmt == "json":
        console.print_json(json.dumps(data, indent=2))
        return
    if fmt == "markdown":
        _render_analysis_markdown(data)
        return
    _render_analysis_text(data)


def _render_analysis_text(data: dict) -> None:
    period = data.get("period", {})
    console.rule("[bold]Meeting Trend Analysis[/bold]")
    console.print(
        f"[dim]Period:[/dim] {period.get('from','?')} → {period.get('to','?')}   "
        f"[dim]Meetings:[/dim] {data.get('meeting_count', '?')}"
    )
    console.print()

    if data.get("summary"):
        console.print(Panel(data["summary"], title="Summary", border_style="cyan"))
        console.print()

    if data.get("recurring_topics"):
        console.print("[bold]Recurring Topics[/bold]")
        for t in data["recurring_topics"]:
            trend = {"increasing": "↑", "decreasing": "↓", "stable": "→"}.get(
                t.get("trend", ""), ""
            )
            console.print(f"  {trend} {t['topic']} ({t.get('frequency', '?')}×)")
        console.print()

    if data.get("key_decisions"):
        console.print("[bold]Key Decisions[/bold]")
        for d in data["key_decisions"]:
            console.print(f"  • {d}")
        console.print()

    if data.get("open_action_items"):
        console.print("[bold]Open Action Items[/bold]")
        for ai in data["open_action_items"]:
            owner = f" [{ai.get('owner')}]" if ai.get("owner") else ""
            console.print(f"  • {ai['task']}{owner} (since {ai.get('first_mentioned','?')})")
        console.print()

    if data.get("risks_and_concerns"):
        console.print("[bold]Risks & Concerns[/bold]")
        for r in data["risks_and_concerns"]:
            console.print(f"  [red]•[/red] {r}")
        console.print()

    if data.get("recommendations"):
        console.print("[bold]Recommendations[/bold]")
        for r in data["recommendations"]:
            console.print(f"  [green]→[/green] {r}")


def _render_analysis_markdown(data: dict) -> None:
    period = data.get("period", {})
    lines = [
        "# Meeting Trend Analysis",
        f"**Period:** {period.get('from','?')} → {period.get('to','?')}  "
        f"**Meetings analyzed:** {data.get('meeting_count','?')}",
        "",
    ]
    if data.get("summary"):
        lines += ["## Summary", data["summary"], ""]
    if data.get("recurring_topics"):
        lines.append("## Recurring Topics")
        for t in data["recurring_topics"]:
            lines.append(f"- {t['topic']} ({t.get('frequency','?')}× — {t.get('trend','')})")
        lines.append("")
    if data.get("open_action_items"):
        lines.append("## Open Action Items")
        for ai in data["open_action_items"]:
            owner = f" [{ai.get('owner')}]" if ai.get("owner") else ""
            lines.append(f"- {ai['task']}{owner}")
        lines.append("")
    if data.get("recommendations"):
        lines.append("## Recommendations")
        for r in data["recommendations"]:
            lines.append(f"- {r}")
    console.print("\n".join(lines))


def render_search_results(
    results: list[tuple["IndexEntry", list[str]]], query: str
) -> None:
    if not results:
        console.print(f"[dim]No matches for:[/dim] {query}")
        return
    console.print(f"[bold]Search results for:[/bold] [cyan]{query}[/cyan]\n")
    for entry, matches in results:
        console.print(
            f"[bold]{entry.title}[/bold]  [dim]{entry.created_at.strftime('%Y-%m-%d')}  {entry.id}[/dim]"
        )
        for m in matches[:5]:
            console.print(f"  [dim]…[/dim] {m}")
        if len(matches) > 5:
            console.print(f"  [dim]+{len(matches) - 5} more matches[/dim]")
        console.print()


class _RecordingRenderable:
    """Dynamic renderable for the recording live display.

    Uses __rich_console__ so Rich re-evaluates it on every refresh cycle,
    giving a live audio level meter and elapsed time counter.
    """

    def __init__(
        self,
        get_peak: "callable[[], float]",
        get_elapsed: "callable[[], str]",
    ) -> None:
        self._get_peak = get_peak
        self._get_elapsed = get_elapsed

    def __rich_console__(self, console, options):
        peak = self._get_peak()
        bar_len = 30
        filled = int(peak * bar_len)
        bar = "[green]" + "█" * filled + "[/green]" + "░" * (bar_len - filled)
        elapsed = self._get_elapsed()
        content = Text.assemble(
            ("● REC  ", "bold red"),
            (elapsed, "bold white"),
            "\n",
            ("Level: ", "dim"),
            Text.from_markup(bar),
        )
        panel = Panel(
            content,
            title="[bold red]Recording[/bold red]",
            subtitle="Ctrl-C to stop",
        )
        yield from console.render(panel, options)


def make_recording_live(get_peak: "callable[[], float]", get_elapsed: "callable[[], str]") -> Live:
    return Live(_RecordingRenderable(get_peak, get_elapsed), refresh_per_second=8, console=console)


def transcription_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    )

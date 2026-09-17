"""Interactive metadata wizard for vs record / vs import."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from versascribe.display import console


def prompt_metadata(
    *,
    default_title: str = "Untitled Meeting",
    show_diarize: bool = False,
) -> dict[str, Any]:
    """Ask for meeting metadata interactively and return collected values.

    Returns a dict with keys: title, project, participant, tag, diarize.
    Called when the user runs vs record / vs import with no metadata flags.
    """
    console.print()
    console.rule("[dim]Meeting details[/dim]")

    title = Prompt.ask("[bold]Title[/bold]", default=default_title)

    def _csv(prompt: str) -> list[str]:
        raw = Prompt.ask(f"[bold]{prompt}[/bold] [dim](comma-separated, Enter to skip)[/dim]", default="")
        return [v.strip() for v in raw.split(",") if v.strip()]

    projects = _csv("Projects")
    participants = _csv("Participants")
    tags = _csv("Tags")

    diarize = False
    if show_diarize:
        diarize = Confirm.ask("[bold]Speaker diarization?[/bold]", default=False)

    # Summary panel before starting
    lines: list[str] = [f"  [bold]Title[/bold]        {title}"]
    if projects:
        lines.append(f"  [bold]Projects[/bold]     {', '.join(projects)}")
    if participants:
        lines.append(f"  [bold]Participants[/bold] {', '.join(participants)}")
    if tags:
        lines.append(f"  [bold]Tags[/bold]         {', '.join(tags)}")
    if show_diarize:
        lines.append(f"  [bold]Diarize[/bold]      {'yes' if diarize else 'no'}")

    console.print(Panel("\n".join(lines), expand=False, style="dim"))
    console.print()

    return {
        "title": title,
        "project": projects,
        "participant": participants,
        "tag": tags,
        "diarize": diarize,
    }

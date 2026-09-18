"""Textual TUI for interactive meeting replay."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Label, Static

from versascribe.storage.transcript import TranscriptRecord, TranscriptSegment, save_transcript


# ── modal screens ─────────────────────────────────────────────────────────────

class _EditScreen(ModalScreen[Optional[str]]):
    """Edit a segment's text."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Edit segment text  [dim]Enter = save · Esc = cancel[/dim]")
            yield Input(value=self._text, id="inp")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class _SpeakerScreen(ModalScreen[Optional[str]]):
    """Assign a name to a speaker label."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, current: str, known: list[str]) -> None:
        super().__init__()
        self._current = current
        self._known = known

    def compose(self) -> ComposeResult:
        known_hint = "  ".join(self._known) if self._known else "—"
        with Container(id="dialog"):
            yield Label(
                f"Set speaker  [dim]Enter = save · Esc = cancel[/dim]\n"
                f"[dim]Known:[/dim] {known_hint}"
            )
            yield Input(value=self._current, placeholder="e.g. Alice", id="inp")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class _NoteScreen(ModalScreen[Optional[str]]):
    """Add or edit a sidenote on a segment."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, note: str) -> None:
        super().__init__()
        self._note = note

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Sidenote  [dim]Enter = save · Esc = cancel · leave blank to clear[/dim]")
            yield Input(value=self._note, placeholder="Add a note…", id="inp")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── main app ──────────────────────────────────────────────────────────────────

_CSS = """
#meta {
    height: 1;
    padding: 0 1;
    color: $text-muted;
    background: $surface;
}
DataTable {
    height: 1fr;
}
_EditScreen, _SpeakerScreen, _NoteScreen {
    align: center middle;
}
#dialog {
    width: 74;
    height: auto;
    padding: 1 2;
    background: $panel;
    border: round $primary;
}
#dialog Label {
    margin-bottom: 1;
}
"""


class ReplayApp(App[bool]):
    """Interactive replay and editing for a VersaScribe transcript."""

    CSS = _CSS

    _playing: reactive[bool] = reactive(False)

    BINDINGS = [
        Binding("q", "quit_save", "Quit & Save"),
        Binding("backspace", "quit_save", "Back to List", show=False),
        Binding("space", "play_pause", "Play / Pause", priority=True),
        Binding("e", "edit_text", "Edit text"),
        Binding("s", "set_speaker", "Speaker"),
        Binding("n", "add_note", "Note"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, record: TranscriptRecord, path: Path) -> None:
        super().__init__()
        self._record = record
        self._path = path
        self._dirty = False
        self._wav_path: Optional[Path] = self._resolve_wav()

    def _resolve_wav(self) -> Optional[Path]:
        if self._record.source.audio_file:
            p = Path(self._record.source.audio_file)
            if not p.is_absolute():
                p = self._path.parent / p
            if p.exists():
                return p
        return None

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._meta_line(), id="meta")
        yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._record.metadata.title
        self.sub_title = "VersaScribe Replay"
        table = self.query_one(DataTable)
        table.add_column("Time", width=6)
        table.add_column("Speaker", width=18)
        table.add_column("Transcript")
        table.add_column("Note", width=30)
        self._fill_table()
        table.focus()

    def _meta_line(self) -> str:
        r = self._record
        date = r.created_at.strftime("%Y-%m-%d %H:%M")
        ds = int(r.source.duration_seconds)
        dur = f"{ds // 60}m {ds % 60:02d}s"
        n = len(r.transcription.segments)
        parts = [date, dur, f"{n} seg"]
        if r.metadata.project:
            parts.append(", ".join(r.metadata.project))
        if r.metadata.participants:
            parts.append(", ".join(r.metadata.participants))
        if self._wav_path:
            parts.append("▶ playing" if self._playing else "audio ✓")
        else:
            parts.append("no audio")
        return "  |  ".join(parts)

    def watch__playing(self, _value: bool) -> None:
        for widget in self.query("#meta"):
            widget.update(self._meta_line())

    def _fill_table(self, restore_row: int = 0) -> None:
        table = self.query_one(DataTable)
        table.clear()
        sm = self._record.metadata.speaker_map
        for seg in self._record.transcription.segments:
            m, s = divmod(int(seg.start), 60)
            ts = f"{m:02d}:{s:02d}"
            raw = seg.speaker or ""
            display = sm.get(raw, raw)
            note_str = f"✎ {seg.note}" if seg.note else ""
            table.add_row(ts, display, seg.text.strip(), note_str)
        if restore_row and restore_row < len(self._record.transcription.segments):
            table.move_cursor(row=restore_row)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _cur_idx(self) -> int:
        return self.query_one(DataTable).cursor_row

    def _cur_seg(self) -> TranscriptSegment:
        return self._record.transcription.segments[self._cur_idx()]

    def _known_speakers(self) -> list[str]:
        sm = self._record.metadata.speaker_map
        seen: list[str] = []
        for seg in self._record.transcription.segments:
            name = sm.get(seg.speaker or "", seg.speaker or "")
            if name and name not in seen:
                seen.append(name)
        return seen

    # ── actions ───────────────────────────────────────────────────────────────

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_play_pause(self) -> None:
        from versascribe.replay.audio import is_playing, play_from, stop as audio_stop

        if not self._wav_path:
            self.notify("No audio file for this transcript.", severity="warning")
            return
        if is_playing():
            audio_stop()
            self._playing = False
        else:
            seg = self._cur_seg()
            play_from(self._wav_path, seg.start, on_done=self._on_audio_done)
            self._playing = True

    def action_edit_text(self) -> None:
        seg = self._cur_seg()
        idx = self._cur_idx()

        def _apply(new_text: Optional[str]) -> None:
            if new_text is not None:
                seg.text = " " + new_text
                self._dirty = True
                self._fill_table(restore_row=idx)

        self.push_screen(_EditScreen(seg.text.strip()), _apply)

    def action_set_speaker(self) -> None:
        seg = self._cur_seg()
        idx = self._cur_idx()
        raw = seg.speaker or ""
        sm = self._record.metadata.speaker_map
        current_name = sm.get(raw, raw)

        def _apply(new_name: Optional[str]) -> None:
            if new_name is None:
                return
            if raw:
                sm[raw] = new_name
            else:
                seg.speaker = new_name
            meta = self._record.metadata
            if new_name and new_name not in meta.participants:
                meta.participants.append(new_name)
            self._dirty = True
            self._fill_table(restore_row=idx)

        self.push_screen(_SpeakerScreen(current_name, self._known_speakers()), _apply)

    def action_add_note(self) -> None:
        seg = self._cur_seg()
        idx = self._cur_idx()

        def _apply(note: Optional[str]) -> None:
            seg.note = note
            self._dirty = True
            self._fill_table(restore_row=idx)

        self.push_screen(_NoteScreen(seg.note or ""), _apply)

    def _on_audio_done(self) -> None:
        """Called from the audio worker thread when playback ends naturally."""
        self.call_from_thread(setattr, self, "_playing", False)

    def action_quit_save(self) -> None:
        from versascribe.replay.audio import stop as audio_stop

        audio_stop()
        self._playing = False
        if self._dirty:
            self._record.updated_at = datetime.now(timezone.utc)
            save_transcript(self._record, self._path)
        self.exit(self._dirty)

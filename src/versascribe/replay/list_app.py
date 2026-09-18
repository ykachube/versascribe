"""Textual browser for opening and managing transcript records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Label

from versascribe.storage.index import IndexEntry, build_index
from versascribe.storage.transcript import load_transcript, save_transcript


class _TextScreen(ModalScreen[Optional[str]]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, label: str, value: str = "") -> None:
        super().__init__()
        self._label = label
        self._value = value

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"{self._label}  [dim]Enter = save · Esc = cancel[/dim]")
            yield Input(value=self._value, id="input")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


class _ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("enter", "confirm", "Confirm"),
        Binding("escape", "cancel", "Cancel"),
        Binding("n", "cancel", "Cancel"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"{self._message}\n[dim]Enter = delete · Esc = cancel[/dim]")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


_CSS = """
DataTable {
    height: 1fr;
}
_TextScreen, _ConfirmScreen {
    align: center middle;
}
#dialog {
    width: 76;
    height: auto;
    padding: 1 2;
    background: $panel;
    border: round $primary;
}
#dialog Label {
    margin-bottom: 1;
}
"""


class TranscriptListApp(App[Optional[Path]]):
    """Browse transcript records and choose one to replay."""

    CSS = _CSS
    BINDINGS = [
        Binding("enter", "open_record", "Replay"),
        Binding("e", "rename_record", "Rename"),
        Binding("d", "delete_record", "Delete"),
        Binding("q", "quit_browser", "Quit"),
        Binding("escape", "quit_browser", "Quit"),
    ]

    def __init__(self, storage_dir: Path, entries: list[IndexEntry] | None = None) -> None:
        super().__init__()
        self._storage_dir = storage_dir
        self._entries = list(entries) if entries is not None else build_index(storage_dir)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Transcripts"
        self.sub_title = "Enter Replay  E Rename  D Delete  Backspace Back"
        table = self.query_one(DataTable)
        table.add_column("ID")
        table.add_column("Date", width=12)
        table.add_column("Title")
        table.add_column("Duration", width=10)
        table.add_column("Audio file")
        self._fill_table()
        table.focus()

    def _fill_table(self, row: int = 0) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for entry in self._entries:
            minutes, seconds = divmod(int(entry.duration_seconds), 60)
            table.add_row(
                entry.id,
                entry.created_at.strftime("%Y-%m-%d"),
                entry.title,
                f"{minutes}m {seconds:02d}s",
                entry.audio_file or "",
            )
        if self._entries:
            table.move_cursor(row=min(row, len(self._entries) - 1))

    def _current_entry(self) -> Optional[IndexEntry]:
        if not self._entries:
            return None
        return self._entries[self.query_one(DataTable).cursor_row]

    def on_data_table_row_selected(self, _event: DataTable.RowSelected) -> None:
        self.action_open_record()

    def action_open_record(self) -> None:
        entry = self._current_entry()
        if entry:
            self.exit(entry.path)

    def action_rename_record(self) -> None:
        entry = self._current_entry()
        if not entry:
            return

        def _apply(title: Optional[str]) -> None:
            if not title:
                return
            record = load_transcript(entry.path)
            record.metadata.title = title
            record.updated_at = datetime.now(timezone.utc)
            save_transcript(record, entry.path)
            row = self.query_one(DataTable).cursor_row
            self._entries = build_index(self._storage_dir)
            self._fill_table(row)

        self.push_screen(_TextScreen("Edit meeting name", entry.title), _apply)

    def action_delete_record(self) -> None:
        entry = self._current_entry()
        if not entry:
            return

        def _apply(confirmed: bool) -> None:
            if not confirmed:
                return
            from versascribe.commands.delete import _delete_one

            row = self.query_one(DataTable).cursor_row
            _delete_one(entry.path, keep_audio=False, storage_dir=self._storage_dir)
            self._entries = build_index(self._storage_dir)
            self._fill_table(row)

        self.push_screen(_ConfirmScreen(f"Delete '{entry.title}' and its audio?"), _apply)

    def action_quit_browser(self) -> None:
        self.exit(None)
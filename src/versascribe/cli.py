"""Root Typer application, startup checks, and command registration."""

from __future__ import annotations

import shutil

import typer

from versascribe.config import load_config
from versascribe.context import set_config
from versascribe.display import warn_panel
from versascribe.storage.paths import get_audio_dir, get_storage_dir, get_tmp_dir

app = typer.Typer(
    name="vs",
    help="VersaScribe — capture, transcribe, and analyze your meetings.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


@app.callback()
def _startup(ctx: typer.Context) -> None:
    config = load_config()
    set_config(ctx, config)
    get_storage_dir(config)
    get_audio_dir(config)
    get_tmp_dir(config)
    if not shutil.which("ffmpeg"):
        warn_panel(
            "ffmpeg not found. Import of video/non-WAV files will fail.\n"
            "Install with: [bold]brew install ffmpeg[/bold]",
            title="ffmpeg missing",
        )


# Register commands directly — avoids add_typer + Argument quirks in Typer 0.12+
from versascribe.commands.record import record          # noqa: E402
from versascribe.commands.import_ import import_file   # noqa: E402
from versascribe.commands.list_ import list_transcripts  # noqa: E402
from versascribe.commands.show import show              # noqa: E402
from versascribe.commands.search import search          # noqa: E402
from versascribe.commands.tag import tag                # noqa: E402
from versascribe.commands.mom import mom                # noqa: E402
from versascribe.commands.analyze import analyze        # noqa: E402
from versascribe.commands.config import config_cmd      # noqa: E402
from versascribe.commands.delete import delete          # noqa: E402

app.command(name="record")(record)
app.command(name="import")(import_file)
app.command(name="list")(list_transcripts)
app.command(name="show")(show)
app.command(name="search")(search)
app.command(name="tag")(tag)
app.command(name="mom")(mom)
app.command(name="analyze")(analyze)
app.command(name="config")(config_cmd)
app.command(name="delete")(delete)

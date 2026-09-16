"""vs config — view and set configuration values."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from versascribe.context import get_config
from versascribe.config import VALID_KEYS, AppConfig, load_config, save_config
from versascribe.display import console, error_panel, success

_DEFAULTS = AppConfig()


def config_cmd(
    ctx: typer.Context,
    set_val: Optional[str] = typer.Option(None, "--set", help="KEY=VALUE"),
    get_key: Optional[str] = typer.Option(None, "--get", help="Print value for KEY"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all config values"),
    reset_key: Optional[str] = typer.Option(None, "--reset", help="Reset KEY to default"),
    show_path: bool = typer.Option(False, "--show-path", help="Print path to config file"),
) -> None:
    """View or modify VersaScribe configuration."""
    from versascribe.config import CONFIG_PATH

    if show_path:
        console.print(str(CONFIG_PATH))
        return

    cfg = load_config()

    if set_val:
        if "=" not in set_val:
            error_panel("Format: --set KEY=VALUE", title="Invalid format")
            raise typer.Exit(1)
        key, _, value = set_val.partition("=")
        if key not in VALID_KEYS:
            error_panel(f"Unknown key: {key}\nValid keys: {', '.join(sorted(VALID_KEYS))}")
            raise typer.Exit(1)
        _set_field(cfg, key, value)
        save_config(cfg)
        success(f"Set {key} = {value}")
        return

    if get_key:
        if get_key not in VALID_KEYS:
            error_panel(f"Unknown key: {get_key}")
            raise typer.Exit(1)
        console.print(str(getattr(cfg, get_key, "")))
        return

    if reset_key:
        if reset_key not in VALID_KEYS:
            error_panel(f"Unknown key: {reset_key}")
            raise typer.Exit(1)
        default_val = getattr(_DEFAULTS, reset_key)
        setattr(cfg, reset_key, default_val)
        save_config(cfg)
        success(f"Reset {reset_key} to {default_val!r}")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Default")
    for key in sorted(VALID_KEYS):
        val = getattr(cfg, key, "")
        default = getattr(_DEFAULTS, key, "")
        display_val = "***" if key == "claude_api_key" and val else str(val)
        style = "" if val == default else "bold"
        table.add_row(key, display_val, str(default), style=style)
    console.print(table)


def _set_field(cfg: AppConfig, key: str, value: str) -> None:
    field_type = AppConfig.model_fields[key].annotation
    if field_type is bool or field_type == "bool":
        setattr(cfg, key, value.lower() in {"true", "1", "yes"})
    else:
        setattr(cfg, key, value)

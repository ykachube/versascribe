"""Shared context helpers — kept separate to avoid circular imports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from versascribe.config import AppConfig

_CONFIG_KEY = "config"


def get_config(ctx: typer.Context) -> "AppConfig":
    return ctx.obj[_CONFIG_KEY]


def set_config(ctx: typer.Context, config: "AppConfig") -> None:
    ctx.ensure_object(dict)
    ctx.obj[_CONFIG_KEY] = config

"""Anthropic client factory with config guard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from versascribe import ClaudeNotConfiguredError

if TYPE_CHECKING:
    import anthropic
    from versascribe.config import AppConfig


def get_client(config: "AppConfig") -> "anthropic.Anthropic":
    if not config.claude_api_key:
        raise ClaudeNotConfiguredError(
            "Claude API key is not set.\n"
            "Run: [bold]vs config --set claude_api_key=sk-ant-...[/bold]"
        )
    import anthropic

    return anthropic.Anthropic(api_key=config.claude_api_key)

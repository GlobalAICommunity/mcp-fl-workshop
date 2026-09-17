"""Foundry Local model configuration for the offline workshop VM.

The image-building script downloads the model before the event. Learner code
only loads that cached model into memory, so no exercise needs cloud access,
credentials, or a fixed localhost port.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from foundry_local_sdk.openai import ChatClient

load_dotenv()

DEFAULT_MODEL = "qwen3.5-9b"


class ConfigError(RuntimeError):
    """Raised when the prebuilt VM is missing a usable local model."""


@dataclass(frozen=True)
class LocalModel:
    """A loaded Foundry Local model and its native chat client."""

    alias: str
    model_id: str
    client: ChatClient


def get_model_alias() -> str:
    """Return the hardware-independent model alias selected for the lab."""
    return os.getenv("MCP_WORKSHOP_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_local_model() -> LocalModel:
    """Load the pre-cached Foundry Local model and return its chat client."""
    from foundry_local_sdk import Configuration, FoundryLocalManager

    token_setting = os.getenv("MCP_WORKSHOP_MAX_TOKENS", "").strip() or "256"
    try:
        max_tokens = int(token_setting)
    except ValueError as exc:
        raise ConfigError("MCP_WORKSHOP_MAX_TOKENS must be a positive integer.") from exc
    if max_tokens < 1:
        raise ConfigError("MCP_WORKSHOP_MAX_TOKENS must be a positive integer.")

    if FoundryLocalManager.instance is None:
        config = Configuration(app_name="mcp-fastmcp-workshop")
        log_dir = os.getenv("MCP_WORKSHOP_LOG_DIR", "").strip()
        if log_dir:
            from foundry_local_sdk.logging_helper import LogLevel

            logs_path = Path(log_dir).expanduser().resolve()
            logs_path.mkdir(parents=True, exist_ok=True)
            config.logs_dir = str(logs_path)
            config.log_level = LogLevel.DEBUG
            print(f"Foundry Local debug logs: {logs_path}", file=sys.stderr)
        FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance
    alias = get_model_alias()
    model = manager.catalog.get_model(alias)
    if model is None:
        raise ConfigError(
            f"Foundry Local does not know model alias {alias!r}. "
            "The facilitator must rebuild the VM with scripts/prepare_vm.py."
        )
    if not model.supports_tool_calling:
        raise ConfigError(f"Foundry Local model {alias!r} does not support tool calling.")
    if not model.is_cached:
        raise ConfigError(
            f"Foundry Local model {alias!r} is not cached. "
            "The facilitator must run scripts/prepare_vm.py while online, "
            "then distribute the completed VM image."
        )
    if not model.is_loaded:
        model.load()

    client = model.get_chat_client()
    client.settings.temperature = 0.0
    client.settings.max_tokens = max_tokens
    return LocalModel(alias=alias, model_id=model.id, client=client)


def describe(model: LocalModel | None = None) -> str:
    """Return a short description suitable for command-line output."""
    model = model or get_local_model()
    return f"Foundry Local / {model.alias} ({model.model_id})"

"""Foundry Local model configuration for the offline workshop VM.

The image-building script downloads the model before the event. Learner code
only loads that cached model into memory, so no exercise needs cloud access,
credentials, or a fixed localhost port.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from foundry_local_sdk.openai import ChatClient

load_dotenv()

DEFAULT_MODEL = "qwen3.5-0.8b"


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


def select_cpu_variant(model):
    """Select the smallest tool-capable generic CPU variant for portability."""
    generic_cpu_variants = [
        variant
        for variant in model.variants
        if variant.info.runtime is not None
        and variant.info.runtime.execution_provider == "CPUExecutionProvider"
        and "generic-cpu" in variant.id
    ]
    if not generic_cpu_variants:
        raise ConfigError(
            f"Foundry Local model {model.alias!r} has no generic CPU variant."
        )
    tool_capable_variants = [
        variant for variant in generic_cpu_variants if variant.supports_tool_calling
    ]
    if not tool_capable_variants:
        raise ConfigError(
            f"Foundry Local model {model.alias!r} has no tool-capable generic CPU variant."
        )
    selected = min(
        tool_capable_variants,
        key=lambda variant: (
            variant.info.file_size_mb is None,
            variant.info.file_size_mb or 0,
            variant.id,
        ),
    )
    model.select_variant(selected)
    return model


def get_local_model() -> LocalModel:
    """Load the pre-cached Foundry Local model and return its chat client."""
    from foundry_local_sdk import Configuration, FoundryLocalManager

    if FoundryLocalManager.instance is None:
        FoundryLocalManager.initialize(Configuration(app_name="mcp-fastmcp-workshop"))

    manager = FoundryLocalManager.instance
    alias = get_model_alias()
    model = manager.catalog.get_model(alias)
    if model is None:
        raise ConfigError(
            f"Foundry Local does not know model alias {alias!r}. "
            "The facilitator must rebuild the VM with scripts/prepare_vm.py."
        )
    model = select_cpu_variant(model)
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
    client.settings.max_tokens = 256
    return LocalModel(alias=alias, model_id=model.id, client=client)


def describe(model: LocalModel | None = None) -> str:
    """Return a short description suitable for command-line output."""
    model = model or get_local_model()
    return f"Foundry Local / {model.alias} ({model.model_id})"

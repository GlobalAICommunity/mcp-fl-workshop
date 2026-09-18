"""Foundry Local model configuration for the offline workshop VM.

The image-building script downloads the model before the event. Learner code
only loads that cached model into memory, so no exercise needs cloud access,
credentials, or a fixed localhost port.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "qwen3.5-4b"


class ConfigError(RuntimeError):
    """Raised when the prebuilt VM is missing a usable local model."""


@dataclass(frozen=True)
class LocalModel:
    """A loaded Foundry Local model and its v2 session adapter."""

    alias: str
    model_id: str
    client: NativeChatClient


@dataclass
class ChatSettings:
    """Workshop settings translated to Foundry Local v2 request options."""

    max_tokens: int
    temperature: float = 0.0
    tool_choice: dict | str | None = None


@dataclass(frozen=True)
class CompletionFunction:
    name: str
    arguments: str


@dataclass(frozen=True)
class CompletionToolCall:
    id: str
    function: CompletionFunction
    type: str = "function"


@dataclass(frozen=True)
class CompletionMessage:
    content: str
    tool_calls: list[CompletionToolCall]
    role: str = "assistant"


@dataclass(frozen=True)
class CompletionChoice:
    message: CompletionMessage
    finish_reason: str
    index: int = 0


@dataclass(frozen=True)
class CompletionResponse:
    choices: list[CompletionChoice]
    usage: dict[str, int]

    def model_dump_json(self, indent: int | None = None) -> str:
        """Provide the JSON helper used by the diagnostic script."""
        return json.dumps(asdict(self), indent=indent)


class NativeChatClient:
    """Adapt workshop chat dictionaries to Foundry Local v2 typed sessions."""

    def __init__(self, model, max_tokens: int) -> None:
        self.model = model
        self.settings = ChatSettings(max_tokens=max_tokens)

    def complete_chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> CompletionResponse:
        from foundry_local_sdk import (
            ChatSession,
            Request,
            TextItem,
            TextItemType,
        )

        payload = {
            "model": self.model.id,
            "messages": messages,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
        }
        if tools:
            payload["tools"] = tools
        if self.settings.tool_choice:
            payload["tool_choice"] = self.settings.tool_choice

        with ChatSession(self.model) as session:
            with Request() as request:
                request.add_item(
                    TextItem(json.dumps(payload), TextItemType.OPENAI_JSON)
                )

                with session.process_request(request) as response:
                    result = json.loads(response.get_item(0).text)

        choice = result["choices"][0]
        message = choice["message"]
        calls = [
            CompletionToolCall(
                id=call["id"],
                type=call.get("type", "function"),
                function=CompletionFunction(
                    name=call["function"]["name"],
                    arguments=call["function"].get("arguments", "{}"),
                ),
            )
            for call in message.get("tool_calls") or []
        ]
        usage = result.get("usage") or {}

        return CompletionResponse(
            choices=[
                CompletionChoice(
                    message=CompletionMessage(
                        content=message.get("content") or "", tool_calls=calls
                    ),
                    finish_reason=choice.get("finish_reason") or "stop",
                )
            ],
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )


def get_model_alias() -> str:
    """Return the hardware-independent model alias selected for the lab."""
    return os.getenv("MCP_WORKSHOP_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_max_tokens() -> int:
    """Return the configured positive output-token budget."""
    token_setting = os.getenv("MCP_WORKSHOP_MAX_TOKENS", "").strip() or "64"
    try:
        max_tokens = int(token_setting)
    except ValueError as exc:
        raise ConfigError("MCP_WORKSHOP_MAX_TOKENS must be a positive integer.") from exc
    if max_tokens < 1:
        raise ConfigError("MCP_WORKSHOP_MAX_TOKENS must be a positive integer.")
    return max_tokens


def get_foundry_configuration():
    """Build the shared Foundry Local SDK configuration."""
    from foundry_local_sdk import Configuration

    config = Configuration(app_name="mcp-fastmcp-workshop")
    log_dir = os.getenv("MCP_WORKSHOP_LOG_DIR", "").strip()
    if log_dir:
        from foundry_local_sdk import LogLevel

        logs_path = Path(log_dir).expanduser().resolve()
        logs_path.mkdir(parents=True, exist_ok=True)
        config.logs_dir = str(logs_path)
        config.log_level = LogLevel.DEBUG
        print(f"Foundry Local debug logs: {logs_path}", file=sys.stderr)
    return config


def complete_smoke_test(
    client, messages: list[dict], tools: list[dict], stage: str = "inference"
):
    """Retry one transient cancellation for an idempotent model smoke test."""
    from foundry_local_sdk.exception import FoundryLocalException

    for attempt in range(2):
        started = time.monotonic()
        try:
            return client.complete_chat(messages, tools)
        except FoundryLocalException as exc:
            elapsed = time.monotonic() - started
            cancelled = "operation was cancelled" in str(exc).lower()
            if not cancelled or attempt == 1:
                raise ConfigError(
                    f"{stage} failed after {elapsed:.1f}s on attempt {attempt + 1}: "
                    f"{exc}"
                ) from exc
            print(
                f"{stage} was cancelled after {elapsed:.1f}s; retrying once.",
                file=sys.stderr,
            )
    raise AssertionError("unreachable")


def complete_agent_smoke_test(client) -> str:
    """Prove the model can call a tool and finish after receiving its result."""
    weather_tool = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a supported city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
    final_tool = {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Finish with a short answer based on the tool result.",
            "parameters": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
            },
        },
    }
    messages = [{"role": "user", "content": "Use get_weather for Pune."}]
    first = complete_smoke_test(
        client, messages, [weather_tool], stage="get_weather completion"
    )
    calls = first.choices[0].message.tool_calls or []
    if not calls or calls[0].function.name != "get_weather":
        raise ConfigError("Model did not emit the required get_weather call.")

    call = calls[0]
    messages.extend(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": '{"city":"Pune","temperature_c":27,"condition":"clear"}',
            },
        ]
    )
    second = complete_smoke_test(
        client, messages, [final_tool], stage="post-tool final_answer completion"
    )
    final_calls = second.choices[0].message.tool_calls or []
    if not final_calls or final_calls[0].function.name != "final_answer":
        raise ConfigError("Model did not emit final_answer after the tool result.")
    try:
        answer = json.loads(final_calls[0].function.arguments or "{}").get("answer")
    except json.JSONDecodeError as exc:
        raise ConfigError("Model emitted invalid JSON for final_answer.") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise ConfigError("Model emitted an empty final_answer.")
    return answer.strip()


def select_cpu_variant(model) -> None:
    """Select the highest-priority CPU variant or report what the catalog offers."""
    variants = list(model.variants)
    for variant in variants:
        runtime = variant.info.runtime
        device_type = getattr(runtime, "device_type", None)
        if getattr(device_type, "value", device_type) == "CPU":
            model.select_variant(variant)
            return

    offered = []
    for variant in variants:
        runtime = variant.info.runtime
        device_type = getattr(runtime, "device_type", "unknown")
        provider = getattr(runtime, "execution_provider", "unknown")
        offered.append(
            f"{variant.id} [{getattr(device_type, 'value', device_type)}/{provider}]"
        )
    details = ", ".join(offered) or "none"
    raise ConfigError(
        f"Foundry Local has no CPU variant for {model.alias!r}. "
        f"Available variants: {details}. Choose a model with a CPU variant before "
        "building the workshop image."
    )


def get_local_model() -> LocalModel:
    """Load the pre-cached Foundry Local model and return its chat client."""
    from foundry_local_sdk import FoundryLocalManager

    max_tokens = get_max_tokens()

    if FoundryLocalManager.instance is None:
        FoundryLocalManager.initialize(get_foundry_configuration())

    manager = FoundryLocalManager.instance
    alias = get_model_alias()
    model = manager.catalog.get_model(alias)
    if model is None:
        raise ConfigError(
            f"Foundry Local does not know model alias {alias!r}. "
            "The facilitator must rebuild the VM with scripts/prepare_vm.py."
        )
    select_cpu_variant(model)
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

    client = NativeChatClient(model, max_tokens)
    return LocalModel(alias=alias, model_id=model.id, client=client)


def describe(model: LocalModel | None = None) -> str:
    """Return a short description suitable for command-line output."""
    model = model or get_local_model()
    return f"Foundry Local / {model.alias} ({model.model_id})"

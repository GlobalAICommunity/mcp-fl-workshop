"""Prepare a Windows VM image for the fully offline workshop.

Run this once while the image builder still has internet access. It downloads
the model variant Foundry Local selects for this hardware and proves it can emit an
OpenAI-compatible tool call. Learner setup never downloads.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from foundry_local_sdk import FoundryLocalManager
from foundry_local_sdk.exception import FoundryLocalException

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from model_config import (  # noqa: E402
    DEFAULT_MODEL,
    ConfigError,
    complete_smoke_test,
    get_foundry_configuration,
    select_gpu_variant,
)


def progress(label: str):
    """Build a single-line download progress callback."""

    def show(percent: float) -> None:
        print(f"\r{label}: {percent:5.1f}%", end="", flush=True)

    return show


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Foundry Local model alias")
    args = parser.parse_args()

    FoundryLocalManager.initialize(get_foundry_configuration())
    manager = FoundryLocalManager.instance

    execution_providers = manager.discover_eps()
    missing_providers = [ep.name for ep in execution_providers if not ep.is_registered]
    if missing_providers:
        print(f"Registering execution providers: {', '.join(missing_providers)}")
        result = manager.download_and_register_eps(
            missing_providers,
            lambda name, percent: print(
                f"\rRegistering {name}: {percent:5.1f}%", end="", flush=True
            ),
        )
        print()
        if not result.success or result.failed_eps:
            failed = ", ".join(result.failed_eps) or result.status
            print(f"Execution provider registration failed: {failed}", file=sys.stderr)
            return 1

    model = manager.catalog.get_model(args.model)
    if model is None:
        print(f"Unknown Foundry Local model alias: {args.model}", file=sys.stderr)
        return 1
    if args.model == DEFAULT_MODEL:
        try:
            select_gpu_variant(model)
        except ConfigError as exc:
            print(exc, file=sys.stderr)
            return 1
    if not model.supports_tool_calling:
        print(f"Model {args.model} does not support tool calling.", file=sys.stderr)
        return 1

    runtime = model.info.runtime
    print(
        f"Selected model {model.alias} -> {model.id} "
        f"({runtime.device_type.value}/{runtime.execution_provider})"
    )
    if not model.is_cached:
        model.download(progress(f"Downloading {model.alias}"))
        print()
    else:
        print("Model is already cached.")

    if not model.is_loaded:
        print("Loading model for a tool-calling smoke test...")
        model.load()

    client = model.get_chat_client()
    client.settings.temperature = 0.0
    client.settings.max_tokens = 64
    client.settings.tool_choice = {"type": "required"}
    tools = [
        {
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
    ]
    messages = [{"role": "user", "content": "Use get_weather for Pune."}]
    started = time.monotonic()
    try:
        response = complete_smoke_test(client, messages, tools)
    except FoundryLocalException as exc:
        elapsed = time.monotonic() - started
        print(
            f"Tool-calling smoke test failed for {model.id} after {elapsed:.1f}s: {exc}",
            file=sys.stderr,
        )
        print(
            "Check available GPU memory and rerun with "
            "$env:MCP_WORKSHOP_LOG_DIR='.\\foundry-local-logs' for native logs.",
            file=sys.stderr,
        )
        return 1
    calls = response.choices[0].message.tool_calls or []
    if not calls or calls[0].function.name != "get_weather":
        print("Model loaded but did not produce the required tool call.", file=sys.stderr)
        return 1

    print(f"Tool-calling smoke test passed: {calls[0].function.name}")
    print("VM model preparation complete. Run scripts/verify_setup.py with networking off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
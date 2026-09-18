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
    complete_agent_smoke_test,
    get_foundry_configuration,
    get_max_tokens,
    NativeChatClient,
    select_cpu_variant,
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

    model = manager.catalog.get_model(args.model)
    if model is None:
        print(f"Unknown Foundry Local model alias: {args.model}", file=sys.stderr)
        return 1
    try:
        select_cpu_variant(model)
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

    client = NativeChatClient(model, get_max_tokens())
    client.settings.tool_choice = {"type": "required"}
    started = time.monotonic()
    try:
        complete_agent_smoke_test(client)
    except (ConfigError, FoundryLocalException) as exc:
        elapsed = time.monotonic() - started
        print(
            f"Tool-calling smoke test failed for {model.id} after {elapsed:.1f}s: {exc}",
            file=sys.stderr,
        )
        print(
            "Check available system memory and CPU load, then rerun with "
            "$env:MCP_WORKSHOP_LOG_DIR='.\\foundry-local-logs' for native logs.",
            file=sys.stderr,
        )
        return 1
    print("Two-turn agent smoke test passed: get_weather -> final_answer")
    print("VM model preparation complete. Run scripts/verify_setup.py with networking off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
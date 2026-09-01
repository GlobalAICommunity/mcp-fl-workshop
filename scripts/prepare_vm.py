"""Prepare a Windows VM image for the fully offline workshop.

Run this once while the image builder still has internet access. It downloads
the selected model's portable CPU variant and proves the model can emit an
OpenAI-compatible tool call. Learner setup never downloads.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from foundry_local_sdk import Configuration, FoundryLocalManager

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from model_config import DEFAULT_MODEL, ConfigError, select_cpu_variant  # noqa: E402


def progress(label: str):
    """Build a single-line download progress callback."""

    def show(percent: float) -> None:
        print(f"\r{label}: {percent:5.1f}%", end="", flush=True)

    return show


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Foundry Local model alias")
    args = parser.parse_args()

    FoundryLocalManager.initialize(Configuration(app_name="mcp-fastmcp-workshop"))
    manager = FoundryLocalManager.instance

    model = manager.catalog.get_model(args.model)
    if model is None:
        print(f"Unknown Foundry Local model alias: {args.model}", file=sys.stderr)
        return 1
    try:
        model = select_cpu_variant(model)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not model.supports_tool_calling:
        print(f"Model {args.model} does not support tool calling.", file=sys.stderr)
        return 1

    print(f"Selected portable CPU model {model.alias} -> {model.id}")
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
    response = client.complete_chat(
        [{"role": "user", "content": "Use get_weather for Pune."}], tools
    )
    calls = response.choices[0].message.tool_calls or []
    if not calls or calls[0].function.name != "get_weather":
        print("Model loaded but did not produce the required tool call.", file=sys.stderr)
        return 1

    print(f"Tool-calling smoke test passed: {calls[0].function.name}")
    print("VM model preparation complete. Run scripts/verify_setup.py with networking off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
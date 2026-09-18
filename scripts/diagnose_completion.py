"""Compare tools-free chat and synthetic tool-history completions, without MCP."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "solution"))

from agent_raw import FINAL_ANSWER_TOOL
from foundry_local_sdk.exception import FoundryLocalException
from model_config import ConfigError, describe, get_local_model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("baseline", "required", "plain"), required=True,
        help="baseline: no tools/history; plain/required: synthetic tool history",
    )
    args = parser.parse_args()
    instruction = (
        "Call final_answer alone with one short sentence."
        if args.mode == "required"
        else "Respond directly with one short sentence; do not call tools."
    )
    messages = [
        {
            "role": "system",
            "content": (
                "This is a diagnostic using synthetic weather, not live data. "
                "The weather tool has already returned all needed facts. "
                + instruction
            ),
        },
        {"role": "user", "content": "What is the weather in Pune?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "diagnostic_weather",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": json.dumps({"city": "Pune"}),
                },
            }],
        },
        {
            "role": "tool",
            "tool_call_id": "diagnostic_weather",
            "content": json.dumps({
                "city": "Pune", "temperature_c": 25, "condition": "sunny",
            }),
        },
    ]
    if args.mode == "baseline":
        messages = [{"role": "user", "content": "Reply with the word hello."}]
    try:
        model = get_local_model()
        client = model.client
        client.settings.tool_choice = {
            "type": "required" if args.mode == "required" else "none"
        }
        print(f"[{describe(model)}]", flush=True)
        scenario = "No tools or history" if args.mode == "baseline" else "Synthetic tool history"
        print(
            f"{scenario}; mode={args.mode}; "
            "API=Foundry Local v2 typed ChatSession; "
            f"max_tokens={client.settings.max_tokens}; no MCP tools executed.",
            flush=True,
        )
        started = time.monotonic()
        try:
            if args.mode == "baseline":
                response = client.complete_chat(messages)
            else:
                response = client.complete_chat(messages, [FINAL_ANSWER_TOOL])
        finally:
            print(f"Native completion elapsed: {time.monotonic() - started:.1f}s", flush=True)
        print(response.model_dump_json(indent=2))
    except (ConfigError, FoundryLocalException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
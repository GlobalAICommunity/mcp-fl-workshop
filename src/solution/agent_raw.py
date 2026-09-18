"""Module 4, part B - a complete local agent loop, written by hand.

This is the whole trick behind every "AI agent" framework, in about forty lines:

    1. Ask the MCP server what tools exist.
    2. Translate those tool schemas into the shape the model API expects.
    3. Send the conversation plus the tool list to the model.
    4. Run travel tools through MCP and append their results.
    5. Repeat until the model calls the host-only final_answer tool.

Foundry Local supplies an OpenAI-compatible native chat client. The model,
prompts, tool calls, and results all remain on the workshop VM.

SDK 1.2.4 reliably parses this model's calls in required-tool mode. A host-only
final_answer function gives the loop an explicit, structured stopping signal.

Run it:

    .venv/Scripts/python src/solution/agent_raw.py "What should I pack for Kochi?"
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from collections.abc import Callable

from fastmcp import Client
from foundry_local_sdk.exception import FoundryLocalException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_client import server_transport  # noqa: E402
from model_config import ConfigError, describe, get_local_model  # noqa: E402

MAX_TURNS = 6

SYSTEM_PROMPT = (
    "Use one travel tool at a time. Use only tool results; do not invent facts. "
    "When done, call final_answer alone with a short answer."
)

FINAL_ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "final_answer",
        "description": "Finish with a short answer based only on tool results.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                }
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}

TOOL_HINTS = {
    "list_destinations": ("cities", "city", "destination", "where", "supported"),
    "get_weather": ("weather", "temperature", "rain", "humid", "today"),
    "get_forecast": ("forecast", "pack", "plan", "trip", "night", "days"),
    "search_flights": ("flight", "fare", "fly", "route", "depart"),
}


def compact_schema(value):
    """Remove generated schema labels that consume tokens without guiding calls."""
    if isinstance(value, dict):
        return {
            key: compact_schema(item)
            for key, item in value.items()
            if key not in {"title", "additionalProperties"}
        }
    if isinstance(value, list):
        return [compact_schema(item) for item in value]
    return value


def mcp_tools_to_openai(tools) -> list[dict]:
    """Translate MCP tool definitions into OpenAI `tools` entries.

    This is the only real 'glue' in the whole loop. Python exposes
    `input_schema`; the JSON field on the wire remains `inputSchema`.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": compact_schema(tool.input_schema),
            },
        }
        for tool in tools
    ]


def tools_for_question(question: str, tools: list[dict]) -> list[dict]:
    """Keep only likely tools; use all travel tools when intent is ambiguous."""
    text = question.lower()
    selected_names = {
        name for name, hints in TOOL_HINTS.items() if any(hint in text for hint in hints)
    }
    if not selected_names:
        return tools
    selected_names.add("list_destinations")
    return [
        tool
        for tool in tools
        if tool["function"]["name"] in selected_names
        or tool["function"]["name"] == "final_answer"
    ]


async def run(
    question: str,
    on_tool_call: Callable[[str, dict], None] | None = None,
    chat_client=None,
    mcp_server=None,
) -> str:
    llm = chat_client
    if llm is None:
        llm = get_local_model().client
    llm.settings.tool_choice = {"type": "required"}

    transport = mcp_server if mcp_server is not None else server_transport()
    async with Client(transport) as mcp:
        all_tools = mcp_tools_to_openai(await mcp.list_tools()) + [FINAL_ANSWER_TOOL]
        tools = tools_for_question(question, all_tools)

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        first_flight: dict | None = None

        for turn in range(1, MAX_TURNS + 1):
            started = time.monotonic()
            try:
                response = await asyncio.to_thread(
                    llm.complete_chat,
                    messages,
                    tools,
                )
            except FoundryLocalException as exc:
                elapsed = time.monotonic() - started
                raise ConfigError(
                    f"Foundry Local completion failed on turn {turn} after "
                    f"{elapsed:.1f}s: {exc}. No automatic retry was attempted. "
                    "Check the Foundry Local logs and VM CPU/memory usage; "
                    "the SDK error alone does not identify the cause."
                ) from exc
            reply = response.choices[0].message

            # Preserve structured calls, but omit the duplicate raw <tool_call>
            # markup that Foundry Local also leaves in message content.
            messages.append(
                {
                    "role": "assistant",
                    "content": "" if reply.tool_calls else (reply.content or ""),
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in (reply.tool_calls or [])
                    ],
                }
            )

            calls = reply.tool_calls or []
            if not calls:
                return reply.content or "(no answer)"

            for call in calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    # Small models occasionally emit malformed JSON. Tell the
                    # model instead of crashing, and let it try again.
                    args = None

                if args is None:
                    output = "Error: arguments were not valid JSON. Try again."
                elif name == "final_answer":
                    answer = args.get("answer")
                    if len(calls) > 1:
                        output = "Error: call final_answer alone on the next turn."
                    elif isinstance(answer, str) and answer.strip():
                        answer = answer.strip()
                        flight_terms = ("lab ", "depart", "hour", "inr", "fares are fictional.")
                        if first_flight and not all(
                            term in answer.lower() for term in flight_terms
                        ):
                            answer = (
                                f"Flight option: {first_flight['flight_number']}, departs "
                                f"{first_flight['departs']}, duration "
                                f"{first_flight['duration_hours']} hours, INR "
                                f"{first_flight['price_inr']}. Fares are fictional.\n\n"
                                f"{answer}"
                            )
                        return answer
                    else:
                        output = "Error: final_answer requires a non-empty answer."
                else:
                    if on_tool_call is None:
                        print(f"  -> calling {name}({args})")
                    else:
                        on_tool_call(name, args)
                    result = await mcp.call_tool(name, args, raise_on_error=False)
                    structured = result.structured_content
                    if result.is_error or structured is None:
                        output = "\n".join(
                            block.text
                            for block in result.content
                            if hasattr(block, "text")
                        )
                    else:
                        compact = (
                            structured["result"]
                            if isinstance(structured, dict)
                            and set(structured) == {"result"}
                            else structured
                        )
                        output = json.dumps(compact, separators=(",", ":"))
                    if name == "search_flights" and not result.is_error:
                        flights = (
                            structured.get("result")
                            if isinstance(structured, dict)
                            else None
                        )
                        if isinstance(flights, list) and flights:
                            first_flight = flights[0]
                    if not result.is_error:
                        completed = {name}
                        if name != "list_destinations":
                            completed.add("list_destinations")
                        tools = [
                            tool
                            for tool in tools
                            if tool["function"]["name"] not in completed
                        ]

                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": output}
                )

        return "Gave up after too many tool-calling turns."


async def main() -> None:
    question = " ".join(sys.argv[1:]) or "What is the weather in Pune?"
    local_model = get_local_model()
    print(f"[{describe(local_model)}]")
    print(f"Q: {question}\n")
    try:
        answer = await run(question)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"\nA: {answer}")


if __name__ == "__main__":
    asyncio.run(main())

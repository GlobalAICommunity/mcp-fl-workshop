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
from pathlib import Path
from collections.abc import Callable

from fastmcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_client import server_transport  # noqa: E402
from model_config import describe, get_local_model  # noqa: E402

MAX_TURNS = 6

SYSTEM_PROMPT = (
    "You are a concise India travel lab assistant. Use the provided tools for "
    "weather and fictional flight questions. Only cities returned by "
    "list_destinations are supported. Base every claim on tool results. If you "
    "use search_flights, include a returned flight number, departure time, "
    "duration, INR price, and the exact sentence 'Fares are fictional.' When "
    "you have enough information, call final_answer with concise plain prose. "
    "Call final_answer alone, never in the same response as a travel tool."
)

FINAL_ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "final_answer",
        "description": (
            "Return a concise response grounded in completed travel tools. If "
            "flights were searched, include one returned flight number, "
            "departure time, duration, INR price, and 'Fares are fictional.' "
            "Call this tool alone."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Concise answer containing relevant returned facts.",
                }
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}


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
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]


async def run(
    question: str,
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> str:
    local_model = get_local_model()
    llm = local_model.client
    llm.settings.tool_choice = {"type": "required"}

    async with Client(server_transport()) as mcp:
        tools = mcp_tools_to_openai(await mcp.list_tools()) + [FINAL_ANSWER_TOOL]

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        first_flight: dict | None = None

        for _ in range(MAX_TURNS):
            response = await asyncio.to_thread(
                llm.complete_chat,
                messages,
                tools,
            )
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
                    output = "\n".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )
                    if name == "search_flights" and not result.is_error:
                        flights = json.loads(output)
                        if isinstance(flights, list) and flights:
                            first_flight = flights[0]

                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": output}
                )

        return "Gave up after too many tool-calling turns."


async def main() -> None:
    question = " ".join(sys.argv[1:]) or "What is the weather in Pune?"
    local_model = get_local_model()
    print(f"[{describe(local_model)}]")
    print(f"Q: {question}\n")
    answer = await run(question)
    print(f"\nA: {answer}")


if __name__ == "__main__":
    asyncio.run(main())

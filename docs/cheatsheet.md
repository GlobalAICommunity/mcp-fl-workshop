# FastMCP 4 workshop cheatsheet

## Attendee commands

Run these from the repository root in PowerShell:

```powershell
.\workshop.ps1 check
.\workshop.ps1 raw
.\workshop.ps1 client
.\workshop.ps1 agent "What is the weather in Pune?"
.\workshop.ps1 web
```

The browser is served at <http://127.0.0.1:7932>. Stop it with `Ctrl+C`.

## Raw protocol calls

```powershell
# Discover the reference server
.\workshop.ps1 raw

# Call a tool
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Pune"}}'

# Target a learner server
.\workshop.ps1 raw server/discover '{}' --server src\workshop\travel_server.py
```

## FastMCP server

```python
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("Bharat Travel Desk")


class Weather(BaseModel):
    city: str
    temperature_c: int


@mcp.tool
def get_weather(
    city: Annotated[str, Field(description="Supported Indian city.")],
) -> Weather:
    """Get fictional current weather for a city."""
    return Weather(city=city, temperature_c=27)


@mcp.resource("travel://destinations")
def destinations() -> str:
    return "Pune, Kochi, Bengaluru"


@mcp.prompt
def plan_a_trip(city: str, nights: int = 3) -> str:
    return f"Plan {nights} nights in {city}."


if __name__ == "__main__":
    mcp.run()
```

## FastMCP client

```python
from pathlib import Path

from fastmcp import Client

server = Path("src/solution/travel_server.py").resolve()

async with Client(server) as client:
    tools = await client.list_tools()
    result = await client.call_tool("get_weather", {"city": "Pune"})
    print(result.structured_content)
```

FastMCP 4 reminders:

- pass a `Path` for a local Python stdio server
- `list_tools()`, `list_resources()`, and `list_prompts()` return lists directly
- `read_resource()` returns a list of content blocks
- `call_tool()` raises on tool errors by default
- pass `raise_on_error=False` only when the caller handles recoverable errors

## MCP tools to model tools

```python
model_tools = [
    {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }
    for tool in await client.list_tools()
]
```

Python uses `input_schema`; MCP JSON uses `inputSchema` on the wire.

## Agent loop

```text
discover tools
repeat up to MAX_TURNS:
    call Foundry Local with messages and tools
    append the assistant's structured calls without duplicate raw markup
    if the model calls final_answer: return its answer
    for each tool call:
        parse arguments
        call it through FastMCP with raise_on_error=False
        append the result with the matching tool_call_id
```

Set `tool_choice` to `{"type": "required"}` and include a host-only
`final_answer(answer)` function alongside the MCP tools. Foundry Local SDK 1.2.4
then returns parsed calls for `qwen3.5-0.8b`; the host handles `final_answer`
without forwarding it to MCP. For flight questions, the host checks that the
answer contains a returned flight number, departure, duration, INR price, and
the fictional-fare disclosure. If any are absent, it inserts a deterministic
summary from the first structured flight result without another model call.

## Foundry Local

```python
from model_config import get_local_model

local_model = get_local_model()
client = local_model.client
response = client.complete_chat(messages, tools)
```

The event image uses cached alias `qwen3.5-0.8b`. Attendee code must not call a
download API. The native chat call is synchronous; async hosts can use
`await asyncio.to_thread(client.complete_chat, messages, tools)`.

## Primitive control

| Primitive | Selected by | Example |
|---|---|---|
| Tool | Model | `get_weather` |
| Resource | Application | `travel://destinations` |
| Prompt | User | `plan_a_trip` |

## Stdio rules

- stdin and stdout carry JSON-RPC
- diagnostics belong on stderr or in a log sink
- validate and authorize every tool request
- bound result size and execution time
- never trust model-generated arguments merely because they match a schema
# Build a FastMCP server

**Time: 20 minutes**

You will create a compact MCP server with typed tools, structured output, a
resource, and a prompt. Later modules use the completed reference server so the
whole room can stay together.

## 1. Create the learner file

Run this from the repository root:

```powershell
New-Item -ItemType Directory -Force src\workshop | Out-Null
New-Item -ItemType File -Force src\workshop\travel_server.py | Out-Null
```

Open `src/workshop/travel_server.py` and add:

```python
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "My Bharat Travel Desk",
    instructions="Use these fictional results only for the workshop.",
)

WEATHER = {
    "kochi": (31, "humid"),
    "pune": (27, "clear"),
    "varanasi": (29, "hazy"),
}


class Weather(BaseModel):
    city: str
    temperature_c: int
    condition: str


@mcp.tool
def list_destinations() -> list[str]:
    """List the Indian cities this lab supports."""
    return sorted(WEATHER)


@mcp.tool
def get_weather(
    city: Annotated[str, Field(description='Indian city, for example "Pune".')],
) -> Weather:
    """Get fictional current weather for a supported city."""
    key = city.strip().lower()
    if key not in WEATHER:
        raise ValueError(f"Unknown city {city!r}. Try: {', '.join(sorted(WEATHER))}.")
    temperature, condition = WEATHER[key]
    return Weather(
        city=key.title(),
        temperature_c=temperature,
        condition=condition,
    )


@mcp.resource("travel://destinations")
def destinations() -> str:
    """A short destination catalogue selected by the application."""
    return "Supported cities: " + ", ".join(city.title() for city in sorted(WEATHER))


@mcp.prompt
def plan_a_trip(city: str, nights: int = 3) -> str:
    """Create a reusable trip-planning request selected by the user."""
    return f"Plan {nights} nights in {city}. Check the weather before suggesting what to pack."


if __name__ == "__main__":
    mcp.run()
```

## 2. Understand what FastMCP generated

`FastMCP` reads ordinary Python information and publishes MCP definitions:

| Python feature | MCP effect |
|---|---|
| Function name | Tool or prompt name |
| Docstring | Description shown to clients and models |
| Type annotation | JSON Schema field type |
| `Field(...)` | Description and validation metadata |
| Pydantic return model | Output schema and structured content |
| Decorator | Primitive registration |

Descriptions influence model behavior, so write them as precise operational
instructions. Type validation is useful, but it is not authorization.

## 3. Compile the server

```powershell
.\.venv\Scripts\python -m py_compile src\workshop\travel_server.py
```

No output means the file compiled.

## 4. Discover your server

Use the raw helper and point it at your file:

```powershell
.\workshop.ps1 raw server/discover '{}' --server src\workshop\travel_server.py
```

Then call the weather tool:

```powershell
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Pune"}}' --server src\workshop\travel_server.py
```

The result includes human-readable content and structured fields derived from
`Weather`.

Try an unsupported city:

```powershell
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Atlantis"}}' --server src\workshop\travel_server.py
```

The failure is returned as a tool result rather than crashing the handler. An
agent could use the supported-city hint to try again; this one-shot raw helper
then exits normally after receiving the response.

## 5. Compare the complete server

The reference implementation adds deterministic forecasts, fictional flights
in INR, parameter constraints, and ten Indian destinations. Open
`src/solution/travel_server.py`, then run:

```powershell
.\workshop.ps1 client
```

Notice that FastMCP 4 list methods return Python lists directly and
`call_tool()` raises for tool errors by default. The reference client passes
`raise_on_error=False` when it intentionally demonstrates recoverable failure.

## Checkpoint

You have exposed tools, a resource, and a prompt from normal typed Python and
observed a successful structured result plus a recoverable error.

Continue to [Run a client and agent loop](04-raw-client.md).
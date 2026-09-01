---
id: server-capabilities
title: Publish typed travel capabilities
order: 1
estimatedMinutes: 20
---

## Create the server

From the repository root, create a learner file:

```powershell
New-Item -ItemType Directory -Force src\workshop | Out-Null
New-Item -ItemType File -Force src\workshop\travel_server.py | Out-Null
```

Add this compact server:

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
    """A destination catalogue selected by the application."""
    return "Supported cities: " + ", ".join(city.title() for city in sorted(WEATHER))


@mcp.prompt
def plan_a_trip(city: str, nights: int = 3) -> str:
    """Create a trip-planning request selected by the user."""
    return f"Plan {nights} nights in {city}. Check the weather before suggesting what to pack."


if __name__ == "__main__":
    mcp.run()
```

FastMCP uses the function names, docstrings, annotations, and Pydantic metadata
to generate model-facing descriptions and JSON Schema. The `Weather` return
type also produces validated structured content.

## Compile and discover

```powershell
.\.venv\Scripts\python -m py_compile src\workshop\travel_server.py
.\workshop.ps1 raw server/discover '{}' --server src\workshop\travel_server.py
```

Call the tool:

```powershell
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Pune"}}' --server src\workshop\travel_server.py
```

Then replace `Pune` with `Atlantis`. The error should explain the supported
cities without crashing the server. An agent can use that message on its next
turn.

## Compare the reference

Open `src/solution/travel_server.py`. It adds deterministic forecasts, fictional
INR flight fares, input constraints, and ten Indian destinations. The remaining
modules use this reference so everyone has the same four tools.

Run its model-free client:

```powershell
.\workshop.ps1 client
```

FastMCP 4 list methods return lists directly. `call_tool()` raises on tool errors
unless the caller explicitly passes `raise_on_error=False` to handle recovery.
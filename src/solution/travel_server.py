"""Bharat travel MCP server - the completed FastMCP 4 implementation.

FastMCP 4 speaks the 2026-07-28 revision of the Model Context Protocol and
negotiates older protocol versions when a compatible client needs them.

All data here is fake and generated deterministically from the city name, so the
server needs no network access and always gives the same answer for the same
question, which makes it a good thing to demo in front of a room.

Run it directly to serve over stdio:

    python src/solution/travel_server.py
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "Bharat Travel Desk",
    instructions=(
        "A deterministic India travel lab. Use weather tools for conditions, "
        "search_flights for routes, and list_destinations when a city is unclear. "
        "All results are fictional and must not be used for real bookings."
    ),
)

# --------------------------------------------------------------------------
# Fake data
# --------------------------------------------------------------------------

DESTINATIONS: dict[str, str] = {
    "bengaluru": "Technology hubs, gardens and a mild plateau climate.",
    "chennai": "Coastal neighbourhoods, music and South Indian cuisine.",
    "delhi": "Historic sites, busy markets and a vast metro network.",
    "hyderabad": "Lakes, historic architecture and a major technology community.",
    "jaipur": "Forts, craft traditions and the Pink City streetscape.",
    "kochi": "A harbour city with backwaters, art and layered history.",
    "kolkata": "Literature, food, tramways and Hooghly riverfronts.",
    "mumbai": "A coastal megacity known for finance, film and local trains.",
    "pune": "Universities, software companies and nearby hill country.",
    "varanasi": "Ancient riverfront ghats, lanes and living traditions.",
}

CONDITIONS = ["clear", "cloudy", "humid", "light rain", "windy", "hazy"]


def _seed(*parts: str) -> int:
    """Stable pseudo-random seed derived from the inputs.

    Using a hash rather than `random` keeps results reproducible across runs and
    machines, which matters when you are demoing live.
    """
    joined = "|".join(parts).lower()
    return int(hashlib.sha256(joined.encode()).hexdigest(), 16)


def _known_city(city: str) -> str:
    key = city.strip().lower()
    if key not in DESTINATIONS:
        known = ", ".join(sorted(DESTINATIONS))
        raise ValueError(f"Unknown city {city!r}. Known cities are: {known}.")
    return key


# --------------------------------------------------------------------------
# Structured output models
# --------------------------------------------------------------------------


class Weather(BaseModel):
    """Current weather for a city."""

    city: str
    temperature_c: int = Field(description="Temperature in degrees Celsius.")
    condition: str = Field(description="Short human-readable sky condition.")
    humidity_pct: int = Field(ge=0, le=100)


class ForecastDay(BaseModel):
    """Weather for a single future day."""

    day: str = Field(description="ISO date in YYYY-MM-DD format.")
    high_c: int
    low_c: int
    condition: str


class Flight(BaseModel):
    """A bookable (and entirely imaginary) flight."""

    flight_number: str
    origin: str
    destination: str
    departs: str = Field(description="Local departure time, 24h HH:MM.")
    duration_hours: float
    price_inr: int = Field(description="Fictional fare in Indian rupees.")


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------


@mcp.tool
def list_destinations() -> list[str]:
    """List every city this travel service knows about."""
    return sorted(DESTINATIONS)


@mcp.tool
def get_weather(
    city: Annotated[str, Field(description='Indian city name, e.g. "Pune".')],
) -> Weather:
    """Get today's weather for a city. Only supported destinations work."""
    key = _known_city(city)
    seed = _seed("weather", key, date.today().isoformat())
    return Weather(
        city=key.title(),
        temperature_c=12 + (seed % 27),
        condition=CONDITIONS[seed % len(CONDITIONS)],
        humidity_pct=40 + (seed % 55),
    )


@mcp.tool
def get_forecast(
    city: Annotated[str, Field(description='Indian city name, e.g. "Kochi".')],
    days: Annotated[int, Field(ge=1, le=7, description="Days ahead to forecast.")] = 3,
    units: Annotated[
        Literal["celsius", "fahrenheit"], Field(description="Temperature units.")
    ] = "celsius",
) -> list[ForecastDay]:
    """Get a multi-day weather forecast for a city."""
    key = _known_city(city)
    if not 1 <= days <= 7:
        raise ValueError("days must be between 1 and 7")

    forecast: list[ForecastDay] = []
    for offset in range(1, days + 1):
        day = date.today() + timedelta(days=offset)
        seed = _seed("forecast", key, day.isoformat())
        low_c = 10 + (seed % 22)
        high_c = low_c + 2 + (seed % 8)
        if units == "fahrenheit":
            low_c = round(low_c * 9 / 5 + 32)
            high_c = round(high_c * 9 / 5 + 32)
        forecast.append(
            ForecastDay(
                day=day.isoformat(),
                high_c=high_c,
                low_c=low_c,
                condition=CONDITIONS[seed % len(CONDITIONS)],
            )
        )
    return forecast


@mcp.tool
def search_flights(
    origin: Annotated[str, Field(description='Indian departure city, e.g. "Delhi".')],
    destination: Annotated[str, Field(description='Indian arrival city, e.g. "Kochi".')],
    max_results: Annotated[
        int, Field(ge=1, le=5, description="Maximum number of flights to return.")
    ] = 3,
) -> list[Flight]:
    """Search for flights between two cities."""
    origin_key = _known_city(origin)
    dest_key = _known_city(destination)
    if origin_key == dest_key:
        raise ValueError("origin and destination must be different cities")
    if not 1 <= max_results <= 5:
        raise ValueError("max_results must be between 1 and 5")

    flights: list[Flight] = []
    for index in range(max_results):
        seed = _seed("flight", origin_key, dest_key, str(index))
        flights.append(
            Flight(
                flight_number=f"LAB {100 + (seed % 800)}",
                origin=origin_key.title(),
                destination=dest_key.title(),
                departs=f"{6 + (seed % 15):02d}:{(seed % 4) * 15:02d}",
                duration_hours=round(1.0 + (seed % 35) / 10, 1),
                price_inr=3000 + (seed % 9000),
            )
        )
    return sorted(flights, key=lambda flight: flight.departs)


# --------------------------------------------------------------------------
# Resource - application-controlled context, not called by the model
# --------------------------------------------------------------------------


@mcp.resource("travel://destinations")
def destinations_catalog() -> str:
    """The full destination catalogue as human-readable text."""
    lines = [f"- {city.title()}: {blurb}" for city, blurb in sorted(DESTINATIONS.items())]
    return "Destinations this travel service covers:\n" + "\n".join(lines)


# --------------------------------------------------------------------------
# Prompt - a reusable, user-selected workflow
# --------------------------------------------------------------------------


@mcp.prompt
def plan_a_trip(city: str, nights: int = 3) -> str:
    """Draft a short trip plan for a city."""
    return (
        f"Plan a {nights}-night trip to {city}.\n\n"
        "Steps:\n"
        f"1. Check the weather forecast for {city} for the next {nights} days.\n"
        f"2. Find flights from Bengaluru to {city}.\n"
        "3. Recommend what to pack based on the forecast, and suggest an itinerary.\n"
    )


if __name__ == "__main__":
    mcp.run()

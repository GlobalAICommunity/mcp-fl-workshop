"""Module 4, part A - talk to the MCP server with no LLM involved.

Before adding a model to the picture, it is worth seeing that an MCP client is a
completely ordinary program: it starts the server, asks what it can do, and calls
things. No intelligence required.

FastMCP 4 infers a stdio transport from the server's `Path`. Passing a bare
string for a Python file is deprecated in v4 and will be removed in v5.

Run it:

    .venv/Scripts/python src/solution/mcp_client.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastmcp import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "src" / "solution" / "travel_server.py"


def server_transport() -> Path:
    """Return the trusted local script FastMCP should launch over stdio."""
    return SERVER


async def main() -> None:
    async with Client(server_transport()) as client:
        print(f"Connected. Protocol revision: {client.protocol_version}\n")

        # 1. Discover what the server offers.
        tools = await client.list_tools()
        print("Tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        print()

        # 2. Call a tool. Arguments are a plain dict matching its input schema.
        weather = await client.call_tool("get_weather", {"city": "Pune"})
        print("get_weather('Pune')")
        print("  structured:", weather.structured_content)
        print("  text      :", weather.content[0].text)
        print()

        # 3. Tool failures come back as a result with is_error set, not as an
        #    exception. That is deliberate: the model is meant to read the error
        #    and try again.
        oops = await client.call_tool(
            "get_weather", {"city": "Atlantis"}, raise_on_error=False
        )
        print("get_weather('Atlantis')")
        print("  is_error:", oops.is_error)
        print("  text    :", oops.content[0].text)
        print()

        # 4. Resources are application-controlled context, not model-called tools.
        resources = await client.list_resources()
        print("Resources:", [str(resource.uri) for resource in resources])
        catalog = await client.read_resource("travel://destinations")
        print(catalog[0].text)
        print()

        # 5. Prompts are user-selected, reusable workflows.
        prompts = await client.list_prompts()
        print("Prompts:", [prompt.name for prompt in prompts])
        prompt = await client.get_prompt(
            "plan_a_trip", {"city": "Kochi", "nights": "4"}
        )
        print(json.dumps(prompt.messages[0].content.text, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "solution"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent_raw import MAX_TURNS, run  # noqa: E402
from approval_demo import mcp as approval_server  # noqa: E402
from travel_server import mcp as travel_server  # noqa: E402


class RepeatingChatClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(tool_choice=None)
        self.calls = 0

    def complete_chat(self, messages, tools):
        self.calls += 1
        call = SimpleNamespace(
            id=f"call-{self.calls}",
            function=SimpleNamespace(name="list_destinations", arguments="{}"),
        )
        message = SimpleNamespace(content="", tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FlightChatClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(tool_choice=None)
        self.calls = 0

    def complete_chat(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            name = "search_flights"
            arguments = (
                '{"origin":"Bengaluru","destination":"Kochi","max_results":1}'
            )
        else:
            name = "final_answer"
            arguments = '{"answer":"A flight is available."}'
        call = SimpleNamespace(
            id=f"call-{self.calls}",
            function=SimpleNamespace(name=name, arguments=arguments),
        )
        message = SimpleNamespace(content="", tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class WorkshopTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_and_structured_flight_output(self) -> None:
        async with Client(travel_server) as client:
            tools = await client.list_tools()
            self.assertIn("search_flights", {tool.name for tool in tools})

            result = await client.call_tool(
                "search_flights",
                {"origin": "Bengaluru", "destination": "Kochi", "max_results": 1},
            )

        flights = result.structured_content["result"]
        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0]["origin"], "Bengaluru")
        self.assertEqual(flights[0]["destination"], "Kochi")

    async def test_invalid_city_is_recoverable(self) -> None:
        async with Client(travel_server) as client:
            result = await client.call_tool(
                "get_weather", {"city": "Atlantis"}, raise_on_error=False
            )

        self.assertTrue(result.is_error)
        self.assertIn("Unknown city", result.content[0].text)

    async def test_agent_loop_stops_at_turn_limit(self) -> None:
        chat_client = RepeatingChatClient()

        answer = await run(
            "Keep calling tools", chat_client=chat_client, mcp_server=travel_server
        )

        self.assertEqual(answer, "Gave up after too many tool-calling turns.")
        self.assertEqual(chat_client.calls, MAX_TURNS)

    async def test_agent_uses_structured_flight_result(self) -> None:
        chat_client = FlightChatClient()

        answer = await run(
            "Find a flight", chat_client=chat_client, mcp_server=travel_server
        )

        self.assertIn("LAB 309", answer)
        self.assertIn("INR 5609", answer)
        self.assertIn("Fares are fictional.", answer)

    async def test_declined_approval_takes_no_action(self) -> None:
        async def decline(message, response_type, params, context):
            return ElicitResult(action="decline")

        async with Client(
            approval_server,
            mode="auto",
            elicitation_handler=decline,
            input_required_max_rounds=2,
        ) as client:
            result = await client.call_tool(
                "hold_flight",
                {"flight_number": "LAB 309", "passenger_name": "Asha"},
            )

        self.assertEqual(result.data, "Hold declined. No action was taken.")


if __name__ == "__main__":
    unittest.main()
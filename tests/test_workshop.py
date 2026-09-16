from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from foundry_local_sdk.exception import FoundryLocalException

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "solution"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent_raw import MAX_TURNS, run  # noqa: E402
from model_config import ConfigError, get_local_model  # noqa: E402
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
    def test_model_output_budget(self) -> None:
        for value, expected in (("", 256), ("128", 128), (" 64 ", 64)):
            with self.subTest(value=value), patch.dict(
                os.environ, {"MCP_WORKSHOP_MAX_TOKENS": value}
            ), patch("foundry_local_sdk.FoundryLocalManager") as manager, patch(
                "model_config.select_cpu_variant", side_effect=lambda model: model
            ):
                model = manager.instance.catalog.get_model.return_value
                local_model = get_local_model()
                self.assertEqual(local_model.client.settings.max_tokens, expected)
                model.load.assert_not_called()

    def test_model_output_budget_rejects_invalid_values(self) -> None:
        for value in ("0", "-1", "1.5", "invalid"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"MCP_WORKSHOP_MAX_TOKENS": value}
            ), patch("foundry_local_sdk.FoundryLocalManager") as manager:
                with self.assertRaisesRegex(ConfigError, "positive integer"):
                    get_local_model()
                manager.initialize.assert_not_called()
                manager.instance.catalog.get_model.assert_not_called()

    def test_native_debug_logging_is_opt_in(self) -> None:
        with TemporaryDirectory() as directory:
            log_dir = Path(directory) / "logs"
            for enabled in (False, True):
                with self.subTest(enabled=enabled):
                    environment = {"MCP_WORKSHOP_LOG_DIR": str(log_dir) if enabled else ""}
                    with patch.dict(os.environ, environment), patch(
                        "foundry_local_sdk.FoundryLocalManager"
                    ) as manager:
                        manager.instance = None
                        manager.initialize.side_effect = ConfigError("initialization probe")
                        with self.assertRaisesRegex(ConfigError, "initialization probe"):
                            get_local_model()

                    config = manager.initialize.call_args.args[0].as_dictionary()
                    self.assertEqual(config["AppName"], "mcp-fastmcp-workshop")
                    self.assertEqual(config["LogLevel"], "Debug" if enabled else "Warning")
                    if enabled:
                        self.assertEqual(config["LogsDir"], str(log_dir.resolve()))
                        self.assertTrue(log_dir.is_dir())
                    else:
                        self.assertNotIn("LogsDir", config)

    async def test_completion_cancellation_does_not_replay_tool(self) -> None:
        chat_client = RepeatingChatClient()
        first_response = chat_client.complete_chat([], [])
        failure = FoundryLocalException(
            "Error during chat completion: Operation was cancelled"
        )
        tool_calls = []

        with patch.object(
            chat_client, "complete_chat", side_effect=[first_response, failure]
        ) as complete_chat:
            with self.assertRaisesRegex(
                ConfigError, r"turn 2 after .*s: .*Operation was cancelled"
            ) as caught:
                await run(
                    "Find a flight",
                    chat_client=chat_client,
                    mcp_server=travel_server,
                    on_tool_call=lambda name, args: tool_calls.append((name, args)),
                )

        self.assertIs(caught.exception.__cause__, failure)
        self.assertEqual(complete_chat.call_count, 2)
        self.assertEqual(tool_calls, [("list_destinations", {})])
        messages = complete_chat.call_args.args[0]
        self.assertEqual(messages[-1]["role"], "tool")
        self.assertEqual(messages[-1]["tool_call_id"], "call-1")

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
from __future__ import annotations

import os
import subprocess
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

from agent_raw import (  # noqa: E402
    FINAL_ANSWER_TOOL,
    MAX_TURNS,
    compact_schema,
    mcp_tools_to_openai,
    run,
    tools_for_question,
)
from model_config import (  # noqa: E402
    DEFAULT_MODEL,
    ConfigError,
    complete_agent_smoke_test,
    complete_smoke_test,
    get_local_model,
    select_cpu_variant,
)
from approval_demo import mcp as approval_server  # noqa: E402
from travel_server import mcp as travel_server  # noqa: E402
from scripts import diagnose_completion  # noqa: E402


class CompletionDiagnosticTests(unittest.TestCase):
    def test_request_shapes(self):
        from foundry_local_sdk.openai.chat_client import ChatClientSettings

        for mode, text_format in (
            ("baseline", False), ("plain", False), ("required", False),
            ("baseline", True), ("plain", True),
        ):
            argv = ["diagnose_completion.py", "--mode", mode]
            if text_format:
                argv.append("--text-format")
            with self.subTest(mode=mode, text_format=text_format), patch.object(
                diagnose_completion, "get_local_model"
            ) as get_model, patch.object(
                diagnose_completion, "describe", return_value="test model"
            ), patch.object(
                sys, "argv", argv
            ), patch("builtins.print"):
                client = get_model.return_value.client
                client.settings = ChatClientSettings(max_tokens=64)
                self.assertEqual(diagnose_completion.main(), 0)
                settings = client.settings._serialize()
                if text_format:
                    self.assertEqual(settings["response_format"], {"type": "text"})
                else:
                    self.assertNotIn("response_format", settings)
                client.complete_chat.assert_called_once()
                self.assertEqual(
                    client.settings.tool_choice,
                    {"type": "required" if mode == "required" else "none"},
                )
                if mode == "baseline":
                    client.complete_chat.assert_called_once_with([
                        {"role": "user", "content": "Reply with the word hello."}
                    ])
                else:
                    messages, tools = client.complete_chat.call_args.args
                    self.assertEqual(
                        [message["role"] for message in messages],
                        ["system", "user", "assistant", "tool"],
                    )
                    self.assertEqual(tools, [FINAL_ANSWER_TOOL])

    def test_text_format_rejects_required_mode(self):
        with patch.object(
            sys, "argv",
            ["diagnose_completion.py", "--mode", "required", "--text-format"],
        ), patch.object(diagnose_completion, "get_local_model") as get_model, patch(
            "sys.stderr"
        ):
            with self.assertRaises(SystemExit) as raised:
                diagnose_completion.main()
            self.assertEqual(raised.exception.code, 2)
            get_model.assert_not_called()


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


class WeatherChatClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(tool_choice=None)
        self.tool_names_by_turn: list[list[str]] = []

    def complete_chat(self, messages, tools):
        self.tool_names_by_turn.append(
            [tool["function"]["name"] for tool in tools]
        )
        if len(self.tool_names_by_turn) == 1:
            name = "get_weather"
            arguments = '{"city":"Pune"}'
        else:
            name = "final_answer"
            arguments = '{"answer":"Pune is clear and 27 C."}'
        call = SimpleNamespace(
            id=f"call-{len(self.tool_names_by_turn)}",
            function=SimpleNamespace(name=name, arguments=arguments),
        )
        message = SimpleNamespace(content="", tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class WorkshopTests(unittest.IsolatedAsyncioTestCase):
    def test_agent_smoke_test_completes_post_tool_turn(self) -> None:
        first_call = SimpleNamespace(
            id="weather-1",
            function=SimpleNamespace(
                name="get_weather", arguments='{"city":"Pune"}'
            ),
        )
        final_call = SimpleNamespace(
            id="final-1",
            function=SimpleNamespace(
                name="final_answer", arguments='{"answer":"Pune is clear."}'
            ),
        )
        client = SimpleNamespace(complete_chat=unittest.mock.Mock())
        client.complete_chat.side_effect = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(tool_calls=[first_call])
                    )
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(tool_calls=[final_call])
                    )
                ]
            ),
        ]

        answer = complete_agent_smoke_test(client)

        self.assertEqual(answer, "Pune is clear.")
        self.assertEqual(client.complete_chat.call_count, 2)
        second_messages, second_tools = client.complete_chat.call_args.args
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertEqual(second_messages[-1]["tool_call_id"], "weather-1")
        self.assertEqual(second_tools[0]["function"]["name"], "final_answer")

    def test_agent_smoke_test_identifies_weather_cancellation(self) -> None:
        cancellation = FoundryLocalException(
            "Error during chat completion: Operation was cancelled"
        )
        client = SimpleNamespace(complete_chat=unittest.mock.Mock())
        client.complete_chat.side_effect = [cancellation, cancellation]

        with (
            patch("model_config.time.monotonic", side_effect=[0, 120, 121, 241]),
            patch("model_config.print") as report,
            self.assertRaisesRegex(
                ConfigError,
                r"get_weather completion failed after 120\.0s on attempt 2",
            ) as caught,
        ):
            complete_agent_smoke_test(client)

        report.assert_called_once_with(
            "get_weather completion was cancelled after 120.0s; retrying once.",
            file=sys.stderr,
        )
        self.assertIs(caught.exception.__cause__, cancellation)
        self.assertEqual(client.complete_chat.call_count, 2)

    def test_agent_smoke_test_identifies_post_tool_cancellation(self) -> None:
        first_call = SimpleNamespace(
            id="weather-1",
            function=SimpleNamespace(
                name="get_weather", arguments='{"city":"Pune"}'
            ),
        )
        first_response = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(tool_calls=[first_call]))
            ]
        )
        cancellation = FoundryLocalException(
            "Error during chat completion: Operation was cancelled"
        )
        client = SimpleNamespace(complete_chat=unittest.mock.Mock())
        client.complete_chat.side_effect = [
            first_response,
            cancellation,
            cancellation,
        ]

        with self.assertRaisesRegex(
            ConfigError, "post-tool final_answer completion failed"
        ) as caught:
            complete_agent_smoke_test(client)

        self.assertIs(caught.exception.__cause__, cancellation)
        self.assertEqual(client.complete_chat.call_count, 3)

    async def test_successful_weather_call_leaves_only_final_answer(self) -> None:
        chat_client = WeatherChatClient()

        answer = await run(
            "What is the weather in Pune?",
            chat_client=chat_client,
            mcp_server=travel_server,
        )

        self.assertEqual(answer, "Pune is clear and 27 C.")
        self.assertEqual(
            set(chat_client.tool_names_by_turn[0]),
            {"list_destinations", "get_weather", "final_answer"},
        )
        self.assertEqual(chat_client.tool_names_by_turn[1], ["final_answer"])

    def test_raw_helper_returns_verbose_tool_error(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "raw_jsonrpc.py"),
                "tools/call",
                '{"name":"get_weather","arguments":{"city":"Atlantis"}}',
                "--server",
                str(REPO_ROOT / "src" / "solution" / "travel_server.py"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"isError": true', completed.stdout)
        self.assertNotIn("Timed out", completed.stderr)

    def test_compacts_model_schema_without_mutating_mcp_schema(self) -> None:
        schema = {
            "title": "WeatherArgs",
            "type": "object",
            "properties": {
                "city": {"title": "City", "type": "string"},
            },
            "required": ["city"],
            "additionalProperties": False,
        }
        tool = SimpleNamespace(
            name="get_weather", description="Get weather.", input_schema=schema
        )

        converted = mcp_tools_to_openai([tool])

        self.assertEqual(
            converted[0]["function"]["parameters"],
            {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        )
        self.assertIn("title", schema)
        self.assertFalse(schema["additionalProperties"])

    def test_routes_weather_question_without_flight_or_forecast_schemas(self) -> None:
        names = [
            "list_destinations",
            "get_weather",
            "get_forecast",
            "search_flights",
        ]
        tools = [
            {"type": "function", "function": {"name": name}} for name in names
        ] + [FINAL_ANSWER_TOOL]

        selected = tools_for_question("What is the weather in Pune?", tools)

        selected_names = {tool["function"]["name"] for tool in selected}
        self.assertEqual(
            selected_names, {"list_destinations", "get_weather", "final_answer"}
        )

    def test_ambiguous_question_keeps_all_tools(self) -> None:
        tools = [
            {"type": "function", "function": {"name": "get_weather"}},
            {"type": "function", "function": {"name": "search_flights"}},
            FINAL_ANSWER_TOOL,
        ]

        self.assertEqual(tools_for_question("Help me decide.", tools), tools)

    def test_selects_cpu_variant_even_when_gpu_variant_is_first(self) -> None:
        cpu = SimpleNamespace(
            id="qwen3.5-0.8b-generic-cpu:1",
            info=SimpleNamespace(
                runtime=SimpleNamespace(
                    device_type="CPU", execution_provider="CPUExecutionProvider"
                )
            ),
        )
        gpu = SimpleNamespace(
            id="qwen3.5-0.8b-generic-gpu:1",
            info=SimpleNamespace(
                runtime=SimpleNamespace(
                    device_type="GPU", execution_provider="WebGpuExecutionProvider"
                )
            ),
        )
        model = SimpleNamespace(
            alias=DEFAULT_MODEL,
            variants=[cpu, gpu],
            select_variant=unittest.mock.Mock(),
        )

        select_cpu_variant(model)

        model.select_variant.assert_called_once_with(cpu)

    def test_rejects_model_without_cpu_variant_and_lists_catalog_variants(self) -> None:
        gpu = SimpleNamespace(
            id="qwen3.5-0.8b-generic-gpu:1",
            info=SimpleNamespace(
                runtime=SimpleNamespace(
                    device_type="GPU", execution_provider="WebGpuExecutionProvider"
                )
            ),
        )
        model = SimpleNamespace(
            alias=DEFAULT_MODEL,
            variants=[gpu],
            select_variant=unittest.mock.Mock(),
        )

        with self.assertRaisesRegex(
            ConfigError,
            r"no CPU variant.*qwen3\.5-0\.8b-generic-gpu:1.*WebGpuExecutionProvider",
        ):
            select_cpu_variant(model)

        model.select_variant.assert_not_called()

    def test_prepare_retries_first_inference_cancellation_once(self) -> None:
        client = SimpleNamespace(complete_chat=unittest.mock.Mock())
        cancellation = FoundryLocalException(
            "Error during chat completion: Operation was cancelled"
        )
        expected = SimpleNamespace()
        client.complete_chat.side_effect = [cancellation, expected]

        response = complete_smoke_test(
            client, [{"role": "user"}], [], stage="weather probe"
        )

        self.assertIs(response, expected)
        self.assertEqual(client.complete_chat.call_count, 2)

    def test_prepare_does_not_retry_other_sdk_failures(self) -> None:
        client = SimpleNamespace(complete_chat=unittest.mock.Mock())
        failure = FoundryLocalException("model failed")
        client.complete_chat.side_effect = failure

        with self.assertRaisesRegex(ConfigError, "inference failed") as caught:
            complete_smoke_test(client, [{"role": "user"}], [])

        self.assertIs(caught.exception.__cause__, failure)
        client.complete_chat.assert_called_once()

    def test_model_output_budget(self) -> None:
        for value, expected in (("", 64), ("128", 128), (" 64 ", 64)):
            with self.subTest(value=value), patch.dict(
                os.environ, {"MCP_WORKSHOP_MAX_TOKENS": value}
            ), patch("foundry_local_sdk.FoundryLocalManager") as manager:
                model = manager.instance.catalog.get_model.return_value
                cpu = SimpleNamespace(
                    id="qwen3.5-0.8b-generic-cpu:1",
                    info=SimpleNamespace(
                        runtime=SimpleNamespace(
                            device_type="CPU",
                            execution_provider="CPUExecutionProvider",
                        )
                    ),
                )
                model.variants = [cpu]
                local_model = get_local_model()
                self.assertEqual(local_model.client.settings.max_tokens, expected)
                manager.instance.catalog.get_model.assert_called_once_with(DEFAULT_MODEL)
                model.select_variant.assert_called_once_with(cpu)
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
"""Check that this machine is ready for the workshop.

Run it from the repo root:

    .venv/Scripts/python scripts/verify_setup.py

It checks the virtualenv, FastMCP server, browser app, and pre-cached Foundry
Local model. It never downloads, so it is safe to run after networking is off.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENV_PYTHON = REPO_ROOT / ".venv" / (
    "Scripts/python.exe" if os.name == "nt" else "bin/python"
)
VENV_PYTHON = Path(os.getenv("MCP_WORKSHOP_PYTHON", DEFAULT_VENV_PYTHON))
EXPECTED_PACKAGE_VERSIONS = {
    "fastmcp": "4.0.0",
    "foundry-local-sdk-winml": "1.2.4",
    "python-dotenv": "1.2.3",
    "starlette": "1.6.0",
    "uvicorn": "0.52.4",
}
EXPECTED_PROTOCOL_VERSION = "2026-07-28"
EXPECTED_TOOL_COUNT = "4"

sys.path.insert(0, str(REPO_ROOT / "src"))

OK, BAD, WARN = "  ok  ", " FAIL ", " warn "
failures: list[str] = []
warnings: list[str] = []


def report(status: str, label: str, detail: str = "", fix: str = "") -> None:
    print(f"[{status}] {label}" + (f" - {detail}" if detail else ""))
    if status == BAD:
        failures.append(f"{label}: {fix or detail}")
    elif status == WARN:
        warnings.append(f"{label}: {fix or detail}")


def run_in(python: Path, code: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [str(python), "-c", code],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def check_python() -> None:
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 11):
        report(OK, "Python version", f"{major}.{minor}")
    else:
        report(BAD, "Python version", f"{major}.{minor}", "Foundry Local needs Python 3.11 or newer.")


def check_server_venv() -> None:
    if not VENV_PYTHON.exists():
        report(BAD, "Virtualenv", "missing", "The VM image is incomplete. Ask the facilitator for a clean image.")
        return
    package_names = tuple(EXPECTED_PACKAGE_VERSIONS)
    code = (
        "import importlib.metadata as m;"
        f"print('|'.join(m.version(name) for name in {package_names!r}))"
    )
    ok, out = run_in(VENV_PYTHON, code)
    if not ok:
        report(BAD, "Virtualenv", "workshop packages are not importable", "Rebuild the VM image from requirements-lock.txt.")
        return
    installed_versions = dict(zip(package_names, out.splitlines()[-1].split("|")))
    mismatches = [
        f"{name}: expected {expected}, found {installed_versions.get(name, 'missing')}"
        for name, expected in EXPECTED_PACKAGE_VERSIONS.items()
        if installed_versions.get(name) != expected
    ]
    if not mismatches:
        report(
            OK,
            "Virtualenv",
            "FastMCP 4.0.0, Foundry Local SDK 1.2.4, all direct pins match",
        )
    else:
        report(
            BAD,
            "Virtualenv",
            "; ".join(mismatches),
            "Package versions do not match requirements-lock.txt. Rebuild the VM image.",
        )


def check_server_runs() -> None:
    if not VENV_PYTHON.exists():
        report(WARN, "MCP server", "skipped", "server virtualenv missing")
        return
    code = "\n".join(
        [
            "import asyncio, sys",
            "sys.path.insert(0, 'src/solution')",
            "from fastmcp import Client",
            "from travel_server import mcp",
            "async def main():",
            "    async with Client(mcp) as c:",
            "        tools = await c.list_tools()",
            "        result = await c.call_tool('get_weather', {'city': 'Pune'})",
            "        print(len(tools), c.protocol_version, result.structured_content['city'])",
            "asyncio.run(main())",
        ]
    )
    ok, out = run_in(VENV_PYTHON, code)
    if not ok or not out:
        report(BAD, "MCP server", "did not start", out[-200:] or "unknown error")
        return
    try:
        count, revision, city = out.splitlines()[-1].split()
    except ValueError:
        report(BAD, "MCP server", "returned an unexpected result", out[-200:])
        return
    if (
        count == EXPECTED_TOOL_COUNT
        and revision == EXPECTED_PROTOCOL_VERSION
        and city == "Pune"
    ):
        report(OK, "MCP server", f"{count} tools, protocol {revision}, city {city}")
    else:
        report(
            BAD,
            "MCP server",
            f"{count} tools, protocol {revision}, city {city}",
            "Expected four tools, protocol 2026-07-28, and a structured Pune result.",
        )


def check_browser_app() -> None:
    ok, out = run_in(
        VENV_PYTHON,
        "import sys;sys.path.insert(0,'src/solution');from web import app;print(len(app.routes))",
    )
    if ok and out.splitlines()[-1] == "2":
        report(OK, "Browser app", "ready")
    else:
        report(BAD, "Browser app", "did not import", out[-200:] or "unknown error")


def check_local_model() -> None:
    try:
        import model_config as mc
    except Exception as exc:  # noqa: BLE001
        report(BAD, "Foundry Local model", f"config error: {exc}")
        return

    try:
        local_model = mc.get_local_model()
    except mc.ConfigError as exc:
        report(BAD, "Foundry Local model", str(exc))
        return

    local_model.client.settings.max_tokens = 64
    local_model.client.settings.tool_choice = {"type": "required"}
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a supported city.",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]
    try:
        response = local_model.client.complete_chat(
            [{"role": "user", "content": "Use get_weather for Pune."}], tools
        )
        calls = response.choices[0].message.tool_calls or []
    except Exception as exc:  # noqa: BLE001
        report(BAD, "Foundry Local model", f"inference failed: {exc}")
        return
    if not calls or calls[0].function.name != "get_weather":
        report(BAD, "Foundry Local model", "model did not emit the required tool call")
        return

    report(
        OK,
        "Foundry Local model",
        f"{local_model.alias} loaded from cache and emitted get_weather",
    )


def main() -> int:
    print("MCP workshop - offline setup check\n")
    check_python()
    check_server_venv()
    check_server_runs()
    check_browser_app()
    if "--skip-model" in sys.argv:
        report(WARN, "Foundry Local model", "skipped by request")
    else:
        check_local_model()

    print()
    if failures:
        print(f"{len(failures)} problem(s) to fix:")
        for item in failures:
            print(f"  - {item}")
        return 1
    if warnings:
        print("Ready, with optional items missing:")
        for item in warnings:
            print(f"  - {item}")
        return 0
    print("All good - you are ready for the offline workshop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

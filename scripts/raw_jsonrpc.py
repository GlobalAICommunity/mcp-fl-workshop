"""Send one raw MCP JSON-RPC request to the local stdio server."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERVER = REPO_ROOT / "src" / "solution" / "travel_server.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", nargs="?", default="server/discover")
    parser.add_argument("params", nargs="?", default="{}")
    parser.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as exc:
        parser.error(f"params must be a JSON object: {exc}")
    if not isinstance(params, dict):
        parser.error("params must be a JSON object")

    params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {
            "name": "raw-python-demo",
            "version": "1.0",
        },
    }
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": args.method,
        "params": params,
    }
    encoded = json.dumps(request)
    print(f"--> {encoded}\n", file=sys.stderr)

    process = subprocess.Popen(
        [sys.executable, str(args.server.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        text=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    process.stdin.write(encoded + "\n")
    process.stdin.flush()
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(process.stdout.readline)
        try:
            response = pending.result(timeout=30)
        except FutureTimeoutError:
            process.kill()
            pending.result(timeout=5)
            print("Timed out waiting for a JSON-RPC response.", file=sys.stderr)
            return 1

    process.stdin.close()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)

    if not response.strip():
        print(process.stderr.read() or "No JSON-RPC response received.", file=sys.stderr)
        return 1
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as exc:
        print(f"Server returned invalid JSON: {exc}\n{response}", file=sys.stderr)
        return 1
    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
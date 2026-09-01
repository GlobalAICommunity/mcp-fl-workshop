# Troubleshooting

Start every diagnosis from the repository root:

```powershell
.\workshop.ps1 check
```

Use the first failed line. During an event, replace an incomplete VM instead of
installing packages or downloading models.

## PowerShell cannot run `workshop.ps1`

If execution is disabled, use a process-scoped policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\workshop.ps1 check
```

If PowerShell says the file does not exist, run `Get-Location` and
`Get-ChildItem`. Change to the repository directory that contains
`workshop.ps1`.

## The virtual environment is missing

Expected path:

```text
.venv\Scripts\python.exe
```

For an attendee, this means the image is incomplete. Restore a clean image.

For an image builder, recreate it while online:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install pip==26.1.2
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
```

## The wrong FastMCP version is installed

The workshop is pinned to `fastmcp==4.0.0`. Check the image interpreter:

```powershell
.\.venv\Scripts\python -c "import importlib.metadata as m; print(m.version('fastmcp'))"
```

If it is not `4.0.0`, rebuild `.venv` from `requirements-lock.txt`. Do not try
to repair a shared event image in place.

## The model alias is unknown or not cached

Typical preflight messages include:

```text
Foundry Local does not know model alias '...'
Foundry Local model '...' is not cached
```

The image builder must run this with internet access:

```powershell
.\workshop.ps1 prepare-vm
```

Then rerun full acceptance under the same Windows account used by attendees.
Model cache state may be user-scoped, so validating as an administrator does not
prove that the attendee profile can load it.

## Foundry Local cannot load the CPU model

Rerun `scripts/prepare_vm.py` while online. Confirm that the selected catalog
alias has a `CPUExecutionProvider` variant and that preparation prints a concrete
ID containing `generic-cpu`. A cache containing only a CUDA or NPU variant is not
sufficient for the portable workshop path.

If preparation still fails, keep the full traceback and reject the image. Do
not fall back to a hosted endpoint during an offline event.

## The model is cached but emits no tool call

The full preflight exposes only `get_weather` and sets `tool_choice` to
`required`. Failure means the runtime is not ready even if ordinary chat works.

Check that the image uses the pinned SDK, the configured alias supports tool
calling, and the preparation smoke test passed. Rebuild or replace the image.
`--skip-model` is for code-only diagnostics, never final acceptance.

## The agent is slow on its first question

Model loading and runtime initialization make the first run slower.
Let the full preflight finish before launching the agent. Facilitators should
warm each image shortly before the session.

If every turn remains too slow, reduce other VM load and verify the event image
on the actual host class. Do not increase `MAX_TURNS`; that can make a poor run
longer rather than better.

## A tool reports an unknown city

This is expected for cities outside the deterministic sample set. Use one of:

```text
Bengaluru, Chennai, Delhi, Hyderabad, Jaipur,
Kochi, Kolkata, Mumbai, Pune, Varanasi
```

The error should reach the model as a recoverable tool result. It is not a
server crash.

## The raw helper returns no response

Compile the target server first:

```powershell
.\.venv\Scripts\python -m py_compile src\workshop\travel_server.py
```

Then use an absolute or repository-relative path after `--server`. A stdio
server must not print diagnostics to stdout because that corrupts JSON-RPC.

## The browser port is already in use

Stop the previous `workshop.ps1 web` process with `Ctrl+C`. To use another port
for diagnostics:

```powershell
.\.venv\Scripts\uvicorn --app-dir src\solution web:app --host 127.0.0.1 --port 7933
```

Open <http://127.0.0.1:7933>.

## The browser returns `Local request failed`

Run the same question through the CLI:

```powershell
.\workshop.ps1 agent "What is the weather in Pune?"
```

If the CLI also fails, use the preflight and model sections above. If only the
browser fails, inspect the Uvicorn terminal and verify that `src/solution/web.py`
imports from the same repository.

## Image-builder interpreter override

Maintainers can run code-only checks against another prepared environment:

```powershell
$env:MCP_WORKSHOP_PYTHON = (Resolve-Path .\.venv-test\Scripts\python.exe).Path
.\.venv-test\Scripts\python scripts\verify_setup.py --skip-model
Remove-Item Env:\MCP_WORKSHOP_PYTHON
```

This does not change the attendee contract: the distributed image must contain
and pass with `.venv`.
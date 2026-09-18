# Check the offline VM

**Time: 5 minutes**

This workshop starts from a prepared Windows VM. The repository, Python virtual
environment, Foundry Local runtime, and tool-capable CPU model are
already present. Your job is to verify the image, not install it.

## 1. Open the workshop folder

Open the repository in VS Code. Then open a PowerShell terminal with
**Terminal > New Terminal**.

Confirm the terminal is at the repository root. It must contain
`workshop.ps1`, `requirements-lock.txt`, `docs`, and `src`:

```powershell
Get-ChildItem
```

All workshop commands assume this location.

## 2. Run the offline check

```powershell
.\workshop.ps1 check
```

The check does not download anything. It verifies:

- Python 3.11 or newer
- FastMCP 4.0.0 and Foundry Local SDK 2.0.1 in `.venv`
- the FastMCP server and protocol negotiation
- the browser application import
- a cached CPU variant of `qwen2.5-1.5b` that can request `get_weather`

A ready image ends with output similar to:

```text
[  ok  ] Python version - 3.11
[  ok  ] Virtualenv - FastMCP 4.0.0, Foundry Local SDK 2.0.1, all direct pins match
[  ok  ] MCP server - 4 tools, protocol 2026-07-28, city Pune
[  ok  ] Browser app - ready
[ .... ] Foundry Local model - locating and loading the cached CPU model; this can take several minutes
[ .... ] Foundry Local model - model loaded; requesting the get_weather tool
[  ok  ] Foundry Local model - qwen2.5-1.5b requested get_weather(Pune)

All good - you are ready for the offline workshop.
```

The `[ .... ]` lines are progress, not failures. Model loading and the CPU
completion can take several minutes. While `python.exe` is using CPU or memory,
leave the check running. If the same stage remains for more than five minutes
and `python.exe` is using almost no CPU, press `Ctrl+C` and ask the facilitator
for help. The check proves that the model can produce the structured tool call
needed by the workshop agent.

## 3. If PowerShell blocks the script

The event image should already allow local scripts. If your terminal reports
that script execution is disabled, use a process-only override:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\workshop.ps1 check
```

This setting disappears when the terminal closes.

## 4. If any check fails

Do not install packages or download a model during the event. Record the failed
line and ask the facilitator for a clean VM or a paired workstation. The image
is the reproducible unit for this workshop.

See [troubleshooting.md](troubleshooting.md) for facilitator diagnostics.

## Checkpoint

You are ready when all five checks show `[  ok  ]` while the VM is offline.
Continue to [MCP basics](02-mcp-basics.md).
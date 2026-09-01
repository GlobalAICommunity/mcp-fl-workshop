---
id: prepare-environment
title: Verify the prepared environment
order: 1
estimatedMinutes: 5
---

## Start from the VM, not an installer

The workshop VM already contains the repository, Python 3.11 or newer, `.venv`,
FastMCP 4.0.0, Foundry Local SDK 1.2.4, and the cached generic CPU variant of
model alias `qwen3.5-0.8b`.

Open the repository in VS Code and create a PowerShell terminal. Confirm the
current directory contains `workshop.ps1`, `docs`, and `src`:

```powershell
Get-ChildItem
```

Run the offline preflight:

```powershell
.\workshop.ps1 check
```

The check verifies the pinned packages, starts the reference FastMCP server,
imports the browser, loads the cached model, and forces a real `get_weather`
tool request. It performs no download.

The final line must be:

```text
All good - you are ready for the offline workshop.
```

If script execution is disabled, apply a terminal-only override and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\workshop.ps1 check
```

If any check still fails, use a clean workshop VM or pair with a working
machine. Do not install packages, download a model, or add credentials during
the event.

## Why the tool-call check matters

Three states are different:

1. the SDK imports
2. generic CPU model files exist in the attendee's cache
3. the runtime loads those files and the model emits a valid tool request

Only the third state proves that the end-to-end agent exercise can work on this
hardware while offline.
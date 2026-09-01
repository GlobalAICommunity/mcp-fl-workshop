# Offline Windows VM image runbook

This runbook separates the **online image build** from the **offline attendee
runtime**. Complete every acceptance step before distributing or cloning the
image.

## Acceptance target

The final VM must let an attendee open PowerShell in the repository and run:

```powershell
.\workshop.ps1 check
```

All checks must pass with networking disabled. The model check must load cached
`qwen3.5-0.8b` and produce a `get_weather` tool request.

## 1. Build a representative base image

Use the same Windows edition, architecture, VM generation, CPU class, memory,
and virtualization settings planned for the event. The workshop selects the
generic CPU model variant for portability, but performance acceptance still
needs representative event hardware.

Install before sealing the image:

- supported 64-bit Windows environment
- Python 3.11 or newer with the `py` launcher
- VS Code with the Python extension
- Git, if facilitators will update the repository before sealing
- this repository in a short, attendee-accessible path

Run all remaining steps as the same non-administrator Windows account that
attendees will use. Treat Foundry Local cache and configuration as user-scoped
unless your image process has proved otherwise.

## 2. Create the workshop environment

From the repository root, while online:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install pip==26.1.2
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
```

Verify the pinned packages:

```powershell
.\.venv\Scripts\python -c "import importlib.metadata as m; print(m.version('fastmcp')); print(m.version('foundry-local-sdk-winml'))"
```

Expected versions:

```text
4.0.0
1.2.4
```

Do not install an unpinned replacement immediately before an event. Update and
accept a new workshop release as a separate change.

## 3. Cache the portable CPU model

Still online, run:

```powershell
.\workshop.ps1 prepare-vm
```

The preparation script:

1. initializes the Foundry Local manager
2. resolves `qwen3.5-0.8b` through the catalog
3. selects its generic `CPUExecutionProvider` variant
4. verifies tool-calling support
5. downloads that concrete model if absent
6. loads it and forces a `get_weather` tool request

Do not interrupt a download. The command must end with:

```text
Tool-calling smoke test passed: get_weather
VM model preparation complete. Run scripts/verify_setup.py with networking off.
```

## 4. Run online smoke tests

```powershell
.\workshop.ps1 check
.\workshop.ps1 raw
.\workshop.ps1 client
.\workshop.ps1 agent "Find a flight from Bengaluru to Kochi and tell me what to pack."
```

Reject the image if the agent never calls a tool, invents an unsupported city
without recovering, or cannot complete within the timing budget on target
hardware.

Start the browser:

```powershell
.\workshop.ps1 web
```

Open <http://127.0.0.1:7932>, submit `What is the weather in Pune?`, confirm a
`get_weather` label and grounded answer, then stop Uvicorn with `Ctrl+C`.

## 5. Perform offline acceptance

Disconnect networking at the hypervisor or VM settings. Do not rely only on an
application firewall rule. Restore or restart the VM so the test includes a
cold process and proves that no previous model process is carrying the run.

Under the attendee account, run:

```powershell
.\workshop.ps1 check
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Pune"}}'
.\workshop.ps1 agent "Find a flight from Bengaluru to Kochi and tell me what to pack."
```

Acceptance requires:

- FastMCP exactly 4.0.0
- Foundry Local SDK exactly 1.2.4
- negotiated MCP revision `2026-07-28`
- four reference tools and a structured Pune result
- browser app import success
- cached model tool-call smoke test success
- a complete multi-tool agent answer with fictional INR fares
- no network prompt, sign-in dialog, download, or credential request

Run the browser smoke test offline as well if the image will be used for the
browser module.

## 6. Seal the image

Before taking the final snapshot or template:

- close running Python, Uvicorn, and model processes
- remove secrets, tokens, unrelated shell history, and temporary downloads
- keep `.venv`, the Foundry Local runtime, and the generic CPU model cache
- keep the prepared attendee profile intact
- ensure `.env` is absent or contains only `MCP_WORKSHOP_MODEL=qwen3.5-0.8b`
- open VS Code at the repository root for the attendee
- record the repository revision and image checksum

Be careful with profile cleanup or generalization tools. If they create a new
user or remove local application data, they can silently remove the model cache.
Always boot one VM cloned from the sealed artifact and repeat offline acceptance.

## 7. Event-day sampling

Before doors open, sample several distributed VMs, including machines on
different hosts. Run the full check and one agent question. Keep known-good cold
spares available.

The event should not depend on repairing images. The recovery order is:

1. restart the command once
2. move the attendee to a clean VM
3. pair with a working workstation
4. continue with the model-free client if necessary

Do not enable networking or distribute shared cloud credentials as an improvised
fallback.

## Release record

For each image release, record:

| Field | Value |
|---|---|
| Repository revision | |
| Image identifier and checksum | |
| Windows build | |
| Python version | |
| FastMCP version | `4.0.0` |
| Foundry Local SDK | `1.2.4` |
| Model alias and concrete ID | `qwen3.5-0.8b` / `qwen3.5-0.8b-generic-cpu:3` |
| VM hardware profile | |
| Online preparation date | |
| Offline acceptance date and tester | |
| Cold-clone acceptance result | |
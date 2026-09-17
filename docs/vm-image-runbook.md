# Offline Windows VM image runbook

This runbook separates the **online image build** from the **offline attendee
runtime**. Complete every acceptance step before distributing or cloning the
image.

## Acceptance target

The final VM must let an attendee open PowerShell 7.3 or newer in the repository,
complete the terminal setup in section 3, and run the readiness check in
section 5.

**Image builders: complete sections 1-4 before running the check.** A fresh
repository download does not include the `.venv` Python virtual environment
or the cached model. The check verifies these prerequisites; it does not create
or install them.

All checks must pass with networking disabled. The model check must load cached
`qwen3.5-9b` and produce a `get_weather` tool request.

## 1. Create the virtual environment first

Before running any workshop script, create `.venv` in the repository root.
A virtual environment keeps this workshop's Python packages separate from
other projects. A repository download does not include it.

For this step, use standard 64-bit CPython 3.14 with the `py` launcher, PowerShell
7.3 or newer, and the complete extracted repository. Install these prerequisites
first if they are missing. Use the same non-administrator Windows account and
final repository path that attendees will use.

From Command Prompt or Windows PowerShell, open PowerShell 7:

```powershell
pwsh -NoProfile
```

Inside that session, run each command separately and stop if one fails. Adjust
the example folder to your extracted repository path:

```powershell
Set-Location "$HOME\Desktop\MCP-Workshop"
Get-Item .\workshop.ps1, .\requirements-lock.txt
py -3.14 --version
py -3.14 -m venv .venv
Test-Path .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe --version
```

`Get-Item` must find both repository files before you create the environment.
If either is missing, locate the complete repository using section 3.
`py -3.14` selects Python 3.14 specifically. If it is not found, install or
repair Python 3.14 and its launcher before continuing. If `py` is unavailable
but `python --version` reports Python 3.14.x, use `python -m venv .venv`
instead. Do not use the free-threaded or debug build for this image.

The path check must return `True`, and the last command must report Python
3.14.x. If an existing `.venv` uses another Python version, close processes
using it and rename it to an unused backup name before creating a fresh
environment. Do not reuse its installed packages; install the lock file in
section 3. The launcher explicitly uses `.venv\Scripts\python.exe`; activating
another environment such as `.venv-v4` does not change that path. Activation
of the workshop's `.venv` is included in section 3 after the script-policy setup.

If you see "Workshop virtual environment is missing" while building the image,
complete this step before retrying. If an attendee sees that error on a
distributed VM, replace it with a prepared image rather than installing
during the offline lab.

**Do not run the readiness check yet.** Creating `.venv` fixes the missing-path
error, but you must still install the pinned packages in section 3 and prepare
the model in section 4.

## 2. Build a representative base image

Use the same Windows edition, architecture, VM generation, GPU and CPU class,
memory, and virtualization settings planned for the event. Foundry Local selects
the best compatible model variant, so acceptance needs representative hardware.

Install before sealing the image:

- supported 64-bit Windows environment
- PowerShell 7.3 or newer (`pwsh`), not Windows PowerShell 5.1
- standard 64-bit CPython 3.14 with the `py` launcher
- latest supported Microsoft Visual C++ v14 Redistributable (x64)
- VS Code with the Python extension
- Git, if facilitators will update the repository before sealing
- this repository in a short, attendee-accessible path

ONNX Runtime's [Windows requirements](https://onnxruntime.ai/docs/install/#requirements)
include the Visual C++ runtime. Have the image administrator install the
[official x64 redistributable](https://aka.ms/vc14/vc_redist.x64.exe)
while online, restarting if the installer requests it. Installing Python
packages does not install this system prerequisite. Record the installed
redistributable version with the image release.

Run all remaining steps as the same non-administrator Windows account that
attendees will use. Treat Foundry Local cache and configuration as user-scoped
unless your image process has proved otherwise.

## 3. Configure the terminal and install packages

### Open PowerShell 7 and locate the repository

From Command Prompt or Windows PowerShell, start PowerShell 7:

```powershell
pwsh -NoProfile
```

Run the remaining commands inside that PowerShell session. Change to your
extracted repository folder; adjust this example if you used a different path:

```powershell
Set-Location "$HOME\Desktop\MCP-Workshop"
$PSVersionTable.PSVersion
$PSNativeCommandArgumentPassing = 'Windows'
Get-ChildItem
Test-Path .\workshop.ps1
```

Confirm the version is at least 7.3 and `Test-Path` returns `True`. The argument
setting preserves embedded JSON quotes when passing arguments to Python. It
does not enable this behavior in Windows PowerShell 5.1.

The repository root must contain `workshop.ps1`, `requirements-lock.txt`,
`scripts`, and `src`. If the script is not found, search the extracted folder:

```powershell
Get-ChildItem -Path . -Filter workshop.ps1 -File -Recurse |
	Select-Object FullName
```

If a path appears, change to its containing directory. ZIP extraction can
create a nested folder. If nothing appears, download and extract the complete
accepted repository revision or branch containing the launcher. A download of
`main` is not necessarily the accepted workshop release. An error saying the
script is "not recognized" is a path or missing-file problem, not an execution
policy problem.

### Allow trusted workshop scripts

Review the downloaded repository before unblocking its scripts. In the
PowerShell 7 session, run:

```powershell
Get-ExecutionPolicy -List
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
Get-ChildItem -LiteralPath . -Filter *.ps1 -File -Recurse |
	Unblock-File
```

This removes the internet download marker from PowerShell scripts in this
folder and its subfolders; it does not execute them. `RemoteSigned` permits
unsigned local scripts. The process setting applies only to this terminal and
its child processes and disappears when the terminal closes. Repeat the
terminal setup after a restart or when opening a new terminal unless the image
already has an approved effective policy that permits these scripts.

If a signing error persists, inspect `Get-ExecutionPolicy -List` in the failing
PowerShell 7 session. `MachinePolicy` and `UserPolicy` override process settings.
If either requires signed scripts, obtain a signed script or an approved policy
change from the image administrator; do not attempt to override Group Policy.

### Activate the workshop environment

In the same PowerShell session, from the repository root, run:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
(Get-Command python).Source
```

The prompt normally starts with `(.venv)`. Confirm that the version is Python
3.14.x and the executable path ends in `MCP-Workshop\.venv\Scripts\python.exe`
(with your repository folder name if different). Stop if either check is wrong.
Activation makes `python` and `pip` use this environment in the current terminal.
Repeat it whenever you open a new terminal; activation is not retained after a
restart. The commands below still use the explicit environment path so their
interpreter selection does not depend on activation.

Do not run the workshop check yet. Confirm you created the virtual environment
in section 1, install the packages below, and prepare the model in section 4
first. Do not execute every PowerShell script
indiscriminately; invoke the required workshop action.

### Install the pinned packages while online

Creating `.venv` alone is not enough. Install the workshop dependencies into
that environment, stopping if either command fails:

```powershell
.\.venv\Scripts\python.exe -m pip install pip==26.1.2
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Verify the pinned packages:

```powershell
.\.venv\Scripts\python.exe -c "import importlib.metadata as metadata; print(metadata.version('fastmcp')); print(metadata.version('foundry-local-sdk-winml'))"
```

Expected versions:

```text
4.0.0
1.2.4
```

Do not install an unpinned replacement immediately before an event. Update and
accept a new workshop release as a separate change.

## 4. Cache the GPU model

Still online, run:

```powershell
.\workshop.ps1 prepare-vm
```

The preparation script:

1. initializes the Foundry Local manager
2. discovers and registers execution providers available on the VM
3. resolves `qwen3.5-9b` through the refreshed catalog
4. explicitly selects the highest-priority GPU variant and rejects CPU fallback
5. verifies tool-calling support
6. downloads that concrete model if absent
7. loads it and forces a `get_weather` tool request

Do not interrupt a download. The command must end with:

```text
Tool-calling smoke test passed: get_weather
VM model preparation complete. Run scripts/verify_setup.py with networking off.
```

### If ONNX Runtime cannot load

An error naming `onnxruntime_core\bin\onnxruntime.dll` "or one of its
dependencies" occurs during native runtime initialization, before model
download. It does not by itself prove a Python 3.14 incompatibility. The SDK
already supplies the full DLL path; changing that path is not the first fix.

From the repository root on the failing VM, check the file:

```powershell
Test-Path .\.venv\Lib\site-packages\onnxruntime_core\bin\onnxruntime.dll
```

If this returns `True`, the DLL exists but a dependency may be missing. Have
the image administrator install or repair the x64 Visual C++ redistributable
from section 2. Restart if requested, repeat the terminal setup and activation
in section 3, and retry `.\workshop.ps1 prepare-vm`.

If this returns `False`, the native package installation is incomplete or the
file was removed. Review Windows Security protection history without disabling
protection. While online, restore the pinned package and check dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir --no-deps onnxruntime-core==1.26.0
.\.venv\Scripts\python.exe -m pip check
Test-Path .\.venv\Lib\site-packages\onnxruntime_core\bin\onnxruntime.dll
```

Stop if installation fails or the file remains absent. Do not substitute
`onnxruntime` or `onnxruntime-gpu` for the pinned `onnxruntime-core` package.
If the file exists and loading still fails after runtime repair, capture the
Windows edition/build, Python architecture, installed package versions, and
full traceback for further native dependency diagnosis. Do not seal the image
until `prepare-vm` and offline acceptance pass.

## 5. Run online smoke tests

Only continue after creating `.venv`, installing the pinned packages, and
successfully preparing the model in sections 1-4. Inside the configured
PowerShell 7 session, run:

```powershell
.\workshop.ps1 check
.\workshop.ps1 test
.\workshop.ps1 raw
.\workshop.ps1 client
.\workshop.ps1 agent "Find a flight from Bengaluru to Kochi and tell me what to pack."
```

Alternatively, select PowerShell 7 explicitly for the readiness check:

```powershell
pwsh -NoProfile -ExecutionPolicy RemoteSigned -File .\workshop.ps1 check
```

The `test` action runs the workshop unit tests and content validator. All must
pass on the image's Python 3.14 interpreter before accepting the image. The
project's minimum remains Python 3.11; this runbook selects 3.14 for the VM.

Reject the image if the agent never calls a tool, invents an unsupported city
without recovering, or cannot complete within the timing budget on target
hardware.

Start the browser:

```powershell
.\workshop.ps1 web
```

Open <http://127.0.0.1:7932>, submit `What is the weather in Pune?`, confirm a
`get_weather` label and grounded answer, then stop Uvicorn with `Ctrl+C`.

### If native inference is cancelled

Repeated cancellation near 120 seconds suggests a deadline, but does not
identify its source. A successful tool call followed by a failed completion
is not a script-permission or missing-model error. Capture native debug logs
and test a smaller output budget in the same PowerShell session:

```powershell
$env:MCP_WORKSHOP_LOG_DIR = "$env:TEMP\MCP-Workshop-Logs"
$env:MCP_WORKSHOP_MAX_TOKENS = '128'
.\workshop.ps1 agent "Find a flight from Bengaluru to Kochi and tell me what to pack."
Get-ChildItem -LiteralPath $env:MCP_WORKSHOP_LOG_DIR -File -Recurse |
	ForEach-Object { Get-Content -LiteralPath $_.FullName -Tail 80 }
```

The default output limit is 256 tokens per completion. The override is a
diagnostic experiment, not a timeout extension or a confirmed cancellation
fix. A smaller budget can truncate tool arguments or omit requested content.
Check both the flight facts and weather-grounded packing advice; an incomplete
answer does not pass acceptance. Record elapsed time and CPU/memory usage on
the failing VM. Debug logs may contain prompts and tool results; review them
before sharing and remove diagnostic logs before sealing the image.

Restore defaults after the experiment:

```powershell
Remove-Item Env:MCP_WORKSHOP_MAX_TOKENS -ErrorAction SilentlyContinue
Remove-Item Env:MCP_WORKSHOP_LOG_DIR -ErrorAction SilentlyContinue
```

## 6. Perform offline acceptance

Disconnect networking at the hypervisor or VM settings. Do not rely only on an
application firewall rule. Restore or restart the VM so the test includes a
cold process and proves that no previous model process is carrying the run.

Under the attendee account, reopen PowerShell 7 in the repository and repeat
the terminal setup in section 3, including the process-only execution policy
if needed. Do not repeat package installation or model downloads. Run:

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

## 7. Seal the image

Before taking the final snapshot or template:

- close running Python, Uvicorn, and model processes
- remove secrets, tokens, unrelated shell history, and temporary downloads
- keep `.venv`, the Foundry Local runtime, and the hardware-selected model cache
- keep the prepared attendee profile intact
- verify trusted scripts are unblocked and the approved terminal setup works
	after reboot; a process-only execution policy is not saved in the image
- ensure `.env` is absent or contains only `MCP_WORKSHOP_MODEL=qwen3.5-9b`
- open VS Code at the repository root with a PowerShell 7 terminal profile
- record the repository revision and image checksum

Be careful with profile cleanup or generalization tools. If they create a new
user or remove local application data, they can silently remove the model cache.
Always boot one VM cloned from the sealed artifact and repeat offline acceptance.

## 8. Event-day sampling

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
| PowerShell version and argument-passing mode | |
| Execution policy and trusted-script unblocking verified | |
| Python version | |
| FastMCP version | `4.0.0` |
| Foundry Local SDK | `1.2.4` |
| Model alias and concrete ID | `qwen3.5-9b` / record the ID printed by `prepare-vm` |
| VM hardware profile | |
| Online preparation date | |
| Offline acceptance date and tester | |
| Cold-clone acceptance result | |
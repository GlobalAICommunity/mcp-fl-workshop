[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("check", "client", "agent", "approval", "test", "web", "server", "raw", "prepare-vm")]
    [string]$Action = "check",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Workshop virtual environment is missing. Ask the facilitator for a clean VM image."
}

switch ($Action) {
    "check" {
        & $Python scripts\verify_setup.py @Arguments
    }
    "client" {
        & $Python src\solution\mcp_client.py
    }
    "agent" {
        $Question = if ($Arguments.Count) {
            $Arguments -join " "
        } else {
            "Find a flight from Bengaluru to Kochi and tell me what to pack."
        }
        & $Python src\solution\agent_raw.py $Question
    }
    "approval" {
        & $Python src\solution\approval_demo.py
    }
    "test" {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -eq 0) {
            & $Python scripts\validate_content.py
        }
    }
    "web" {
        Write-Host "Open http://127.0.0.1:7932"
        & $Python -m uvicorn --app-dir src\solution web:app --host 127.0.0.1 --port 7932
    }
    "server" {
        & $Python src\solution\travel_server.py
    }
    "raw" {
        & $Python scripts\raw_jsonrpc.py @Arguments
    }
    "prepare-vm" {
        & $Python scripts\prepare_vm.py @Arguments
    }
}

exit $LASTEXITCODE
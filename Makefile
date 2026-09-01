# Optional GNU Make wrapper. The event VM uses workshop.ps1 directly.
#
#   make setup     create the virtualenv
#   make check     verify this machine is ready
#   make server    run the MCP server over stdio
#   make client    module 4 part A — talk to the server, no LLM
#   make agent     module 4 part B — the hand-written agent loop
#   make web       module 5 — the handwritten agent loop in a browser
#   make jsonrpc   module 2 — poke the server with raw JSON-RPC
#   make prepare-vm download the model while building the online VM image
#   make clean     remove the virtualenv

PY ?= py -3.11
SERVER_PY := .venv/Scripts/python.exe
Q ?= Find a flight from Bengaluru to Kochi and tell me what to pack.

.PHONY: setup check server client agent web jsonrpc prepare-vm clean

setup: .venv
	@echo
	@echo "Setup complete. Now run: make check"

.venv:
	$(PY) -m venv .venv
	$(SERVER_PY) -m pip install pip==26.1.2
	$(SERVER_PY) -m pip install -r requirements-lock.txt

check:
	$(SERVER_PY) scripts/verify_setup.py

server:
	$(SERVER_PY) src/solution/travel_server.py

client:
	$(SERVER_PY) src/solution/mcp_client.py

agent:
	$(SERVER_PY) src/solution/agent_raw.py "$(Q)"

web:
	@echo "Open http://127.0.0.1:7932"
	$(SERVER_PY) -m uvicorn --app-dir src/solution web:app --host 127.0.0.1 --port 7932

jsonrpc:
	$(SERVER_PY) scripts/raw_jsonrpc.py $(METHOD) $(PARAMS)

prepare-vm:
	$(SERVER_PY) scripts/prepare_vm.py

clean:
	powershell -NoProfile -Command "Remove-Item -Recurse -Force .venv"

# Facilitator guide

This guide is for a 90-minute event delivered from prebuilt Windows VMs. The
session has no attendee installation phase and no runtime dependency on event
Wi-Fi, cloud accounts, or API keys.

## Non-negotiable setup

Build and test every image before the event by following
[vm-image-runbook.md](vm-image-runbook.md). The final acceptance test must run
under the attendee Windows account with networking disabled.

Do not distribute an image that only imports the SDK. A ready image must load
the cached model and make it emit `get_weather` in the full preflight.

Keep at least one clean replacement VM for every small group of attendees. A
fresh image is a faster and more reproducible recovery than repairing package or
model state during the session.

## Timing

| Clock | Stage | Outcome |
|---|---|---|
| 00:00-00:05 | Offline check | Every VM passes `workshop.ps1 check` |
| 00:05-00:15 | MCP basics | Learners separate host, client, server, and model |
| 00:15-00:35 | Build server | Learners expose and call a typed FastMCP tool |
| 00:35-01:00 | Client and loop | Learners trace and run the local agent loop |
| 01:00-01:10 | Browser | Learners observe tool behavior in the UI |
| 01:10-01:23 | Production | Group runs approval and identifies safety controls |
| 01:23-01:30 | Assessment | Knowledge check and close |

Do not turn the setup check into an installation tutorial. Replace a bad VM or
pair the attendee with a working machine and continue.

## Room preparation

- Put the repository in the same easy-to-find location on every VM.
- Open VS Code at the repository root before attendees arrive.
- Confirm PowerShell can run the local `workshop.ps1` script.
- Warm the model once with the full preflight.
- Verify port 7932 is free.
- Keep networking disabled if that is part of the event promise.
- Put the sample multi-tool question where everyone can see it.

Recommended question:

```text
Find a flight from Bengaluru to Kochi and tell me what to pack.
```

All travel data and fares are fictional. Say that before the first demo so the
audience does not mistake deterministic sample output for a booking service.

## Teaching notes

### 1. Offline check - 5 minutes

Have everyone run:

```powershell
.\workshop.ps1 check
```

Call out that package presence, model cache presence, and successful tool
calling are three different checks. Move on as soon as each learner has a green
result or a partner.

### 2. MCP basics - 10 minutes

Draw four boxes: host, client, server, model. The most important correction is
that the model does not connect to an MCP server. The host owns both sides of the
agent interaction.

Run `workshop.ps1 raw` briefly. Do not teach JSON-RPC field by field. Use it to
show that FastMCP is convenience over a visible protocol.

### 3. Build server - 20 minutes

Learners type or paste the compact server from module 3. Pause at the tool
signature and ask which text becomes the model-facing description and which
annotation becomes JSON Schema.

The first checkpoint is compilation. The second is a raw tool call. If typing
falls behind, let the learner inspect `src/solution/travel_server.py` and run the
reference client instead of consuming the agent module.

### 4. Client and agent loop - 25 minutes

Run the model-free client first. Ask the room to identify what is absent: there
is no model and no system prompt.

For the agent, trace one iteration only:

1. MCP definitions become model tool definitions.
2. Foundry Local returns a tool request.
3. The host appends the assistant request.
4. FastMCP executes the tool.
5. The host appends a result with the same call ID.

Then run the multi-tool question. Exact prose and order can vary. Judge the demo
by valid tool use and grounded output, not identical wording.

### 5. Browser - 10 minutes

Start `workshop.ps1 web`, show the tool labels, and point out that the UI calls
the same `run()` function as the CLI. Let learners try one valid destination;
Use one valid destination and point out the shared `run()` function. Keep the
invalid-destination example as a facilitator fallback rather than a required
exercise.

### 6. Production - 13 minutes

Ask: "What changes if `search_flights` spends real money?" Collect answers
before showing the checklist. Look for per-user authorization, narrow
credentials, approval, idempotency, audit logging, and bounded results.

Run `workshop.ps1 approval`. Ask one learner to decline and confirm that no
action occurs. Explain that the modern protocol returns `InputRequiredResult`,
the client gathers input, and the original call is reissued with that response.
The model does not approve its own request.

## Common questions

**Why FastMCP instead of writing JSON-RPC?**

The raw demo proves the protocol is ordinary JSON-RPC. FastMCP supplies schema
generation, lifecycle handling, transports, and ergonomic client results so the
lab can focus on capability design.

**Why Foundry Local?**

It keeps prompts, tool requests, and results on the VM and avoids accounts or
network dependencies. The native SDK also avoids managing a separate model
server port.

**Why `qwen3.5-0.8b` on CPU?**

The installed Foundry Local catalog marks the alias as CPU-capable and
tool-calling. It was the smallest candidate that completed the workshop's
required single-tool and multi-tool checks; smaller candidates failed one of
those checks. Selecting the generic CPU variant avoids optional accelerator
registration across cloned VM processes. Image acceptance, not catalog metadata
alone, is the final proof.

**Is a local model automatically secure?**

No. It improves data locality. Tool arguments still need validation and
authorization, and tool content can still contain prompt injection.

**Can attendees use another model?**

Not during this event path. A different alias must be prepared and accepted in
a new image while online.

## When a demo fails

1. Run `workshop.ps1 check` and use its first failed line.
2. If `.venv` or the cache is incomplete, replace the VM.
3. If one inference is poor, retry the concise question once.
4. If tool calling repeatedly fails, use a known-good facilitator VM and trace
   the saved code rather than downloading anything.
5. If port 7932 is occupied, stop the old process or use the CLI demo.

The reference client does not require a model. It remains a useful fallback for
teaching tools, resources, prompts, structured output, and recoverable errors.
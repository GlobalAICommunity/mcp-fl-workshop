# Foundry Local model

The workshop has one supported runtime path: Foundry Local with cached alias
`qwen3.5-0.8b`. It is the smallest catalog candidate that passed both the
required tool-call smoke test and the complete multi-tool workshop scenario.

The direct Python dependency is pinned in `requirements-server.txt`:

```text
foundry-local-sdk-winml==1.2.4
```

`requirements-lock.txt` records the complete dependency closure used to build
the accepted Windows VM image.

## How the model is used

`src/model_config.py` initializes `FoundryLocalManager` once, resolves the alias
through the catalog, selects the generic `CPUExecutionProvider` variant, checks
`supports_tool_calling` and `is_cached`, loads the model if needed, and returns
its native chat client.

```python
local_model = get_local_model()
response = local_model.client.complete_chat(messages, tools)
```

There is no API key, account, cloud endpoint, or separate local HTTP service.
Prompts, tool requests, and tool results stay on the VM. Model calls run in the
host process, while MCP requests and results cross a local stdio subprocess
boundary.

## Alias versus model ID

`qwen3.5-0.8b` is an alias. Foundry Local maps it to concrete model variants.
Workshop configuration uses the alias, then deliberately selects the generic
CPU model ID so a sealed image does not depend on process-local registration of
an optional GPU or NPU provider.

The selected concrete ID is printed by the preparation script and by
`model_config.describe()`.

## Two different lifecycles

### Image builder, online

The image builder downloads the selected model's portable CPU variant:

```powershell
.\workshop.ps1 prepare-vm
```

That script forces one `get_weather` tool request before declaring success.

### Attendee, offline

The attendee only verifies and loads existing assets:

```powershell
.\workshop.ps1 check
```

`get_local_model()` fails with a clear message if the alias is unknown, lacks
tool support, or is not cached. It never silently downloads a missing model.

## Readiness criteria

A model is ready only when all of these are true on representative event
hardware:

1. the catalog resolves the alias
2. the model reports tool-calling support
3. the generic CPU variant is cached under the attendee account
4. the model loads with networking disabled
5. a forced `get_weather` request produces a structured tool call
6. the complete agent answers a multi-tool India travel question

A successful import or cache listing alone is insufficient.

## Changing the model

Facilitators can prepare another catalog alias while building a new image:

```powershell
$CatalogAlias = Read-Host "Foundry Local catalog alias"
.\workshop.ps1 prepare-vm --model $CatalogAlias
$env:MCP_WORKSHOP_MODEL = $CatalogAlias
.\workshop.ps1 check
```

Set the same alias in the final image environment or `.env`, then repeat the
offline acceptance test. Do not change models during the event: an uncached
alias fails by design.

## Performance expectations

The first load is slower than later requests. Warm the model before attendees
arrive, but still test a cold restored VM before distributing the image. Exact
generation speed depends on the VM CPU, memory, execution provider, and host
contention, so measure on the same class of hardware used in the room.

Release validation compared the practical sub-2B candidates on an Intel Core
i7-1185G7 with four cores, eight logical processors, and 64 GB RAM. The same
cold-process three-tool prompt took about 162 seconds with `qwen3.5-0.8b` and
309 seconds with `qwen3.5-2b-text` at a 512-token limit. The final 256-token
configuration completed in about 131 seconds. `qwen3-0.6b` failed the required
tool-call smoke test, while `qwen2.5-0.5b` repeated one tool until the turn limit.
These measurements justify the default; they are comparative results, not a
performance promise for other hardware.
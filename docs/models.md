# Foundry Local model

The workshop has one supported runtime path: Foundry Local with cached alias
`qwen3.5-9b`. Its tool-calling CPU variant runs on the workshop CPU.

The direct Python dependency is pinned in `requirements-server.txt`:

```text
foundry-local-sdk-winml==1.2.4
```

`requirements-lock.txt` records the complete dependency closure used to build
the accepted Windows VM image.

## How the model is used

`src/model_config.py` initializes `FoundryLocalManager` once, resolves the alias
through the catalog, explicitly selects its CPU variant, checks
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

`qwen3.5-9b` is an alias. Foundry Local maps it to concrete model variants. The
workshop explicitly selects `qwen3.5-9b-generic-cpu` so catalog ordering cannot
select the GPU provider.

The selected concrete ID is printed by the preparation script and by
`model_config.describe()`.

## Two different lifecycles

### Image builder, online

The image builder downloads the CPU variant exposed by the SDK catalog:

```powershell
.\workshop.ps1 prepare-vm
```

That script forces one `get_weather` tool request before declaring success.

### Attendee, offline

The attendee only verifies and loads existing assets:

```powershell
.\workshop.ps1 check
```

`get_local_model()` fails with a clear message if the alias is unknown, has no
CPU variant, lacks tool support, or is not cached. It never silently downloads
a missing model or switches to an unsupported accelerator.

## Readiness criteria

A model is ready only when all of these are true on representative event
hardware:

1. the catalog resolves the alias
2. the model reports tool-calling support
3. the CPU variant is cached under the attendee account
4. the model loads with networking disabled
5. a forced `get_weather` request produces a structured tool call
6. a second completion consumes the tool result and calls `final_answer`
7. the complete agent answers a multi-tool India travel question

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

Record cold-load latency, generation speed, system memory use, and the complete
multi-tool acceptance result for the final VM image. These measurements are
specific to the event CPU and virtualization configuration.
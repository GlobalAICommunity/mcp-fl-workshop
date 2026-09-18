---
id: client-and-loop
title: Connect MCP to Foundry Local
order: 1
estimatedMinutes: 25
---

## Start without a model

Run:

```powershell
.\workshop.ps1 client
```

`src/solution/mcp_client.py` passes a trusted server `Path` to FastMCP:

```python
async with Client(SERVER) as client:
    tools = await client.list_tools()
    weather = await client.call_tool("get_weather", {"city": "Pune"})
```

The program discovers tools, calls valid and invalid inputs, reads a resource,
and gets a prompt. There is no model or system prompt. This proves MCP is an
application protocol, not an agent framework.

Typed tool results are available as structured data. FastMCP wraps the Python
return value under `result`:

```python
result = await client.call_tool(
    "search_flights",
    {"origin": "Bengaluru", "destination": "Kochi", "max_results": 1},
)
first_flight = result.structured_content["result"][0]
```

Use `structured_content` for application logic. Keep text as a fallback for
errors and servers that do not publish structured output.

## Load only cached model assets

`src/model_config.py` resolves `qwen2.5-1.5b` through the Foundry Local catalog,
then lets the SDK select the best variant for the VM hardware. It rejects unknown,
non-tool-capable, or uncached models before returning a workshop adapter backed
by a typed native `ChatSession`:

```python
local_model = get_local_model()
llm = local_model.client
```

The image builder performed all downloads. The attendee path only loads local
assets. `complete_chat` is the workshop adapter contract; internally it uses the
SDK v2 typed request and item APIs. Because the adapter is synchronous, the
asynchronous host runs it in a worker thread:

```python
response = await asyncio.to_thread(llm.complete_chat, messages, tools)
```

## Translate the schemas

MCP and model tool calling both use JSON Schema but wrap it differently:

```python
def mcp_tools_to_openai(tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]
```

## Trace one complete turn

Open `src/solution/agent_raw.py` and follow this sequence:

1. discover MCP tools and convert their schemas
2. keep only tools relevant to the question
3. set `tool_choice` to `required` and send the question and tools to Foundry Local
4. read the structured tool call instead of duplicate raw markup
5. execute the selected travel tool with `raise_on_error=False`
6. render successful `structured_content` in the host
7. preserve text errors and retry up to `MAX_TURNS`

Foundry Local SDK 2.0.1 returns an OpenAI-compatible JSON response in
required-tool mode. The workshop adapter translates it to the lesson's compact
response shape. Host-side rendering keeps returned facts exact and avoids a
second model completion, which makes the exercise responsive on a small CPU
model. The turn cap bounds malformed requests and repeatedly failing tools.

## Run the local agent

```powershell
.\workshop.ps1 agent "What is the weather in Pune?"
```

You should see one `get_weather` call and a grounded answer containing the
server's exact temperature, condition, and humidity values.

## Check three code boundaries

Open `src/solution/agent_raw.py` and identify:

1. the property that moves an MCP input schema into a model tool definition
2. the branch between successful structured results and text errors
3. the `MAX_TURNS` limit that stops a model which never finishes

Run the deterministic checks:

```powershell
.\workshop.ps1 test
```
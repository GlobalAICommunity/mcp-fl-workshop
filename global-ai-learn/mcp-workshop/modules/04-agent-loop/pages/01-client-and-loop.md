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

`src/model_config.py` resolves `qwen3.5-0.8b` through the Foundry Local catalog,
then selects its generic CPU variant for VM portability. It rejects unknown,
non-tool-capable, or uncached models before returning a native chat client:

```python
local_model = get_local_model()
llm = local_model.client
```

The image builder performed all downloads. The attendee path only loads local
assets. Because `complete_chat` is synchronous, the asynchronous host runs it in
a worker thread:

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
2. add the host-only `final_answer` function to the model's tool list
3. set `tool_choice` to `required` and send messages and tools to Foundry Local
4. preserve structured calls but omit duplicate raw `<tool_call>` markup
5. return the answer if the model calls `final_answer` alone
6. otherwise execute each travel tool with `raise_on_error=False`
7. serialize successful `structured_content`, while preserving text errors
8. append each result with the matching `tool_call_id`
9. repeat until `final_answer` is called or `MAX_TURNS` is reached

Foundry Local SDK 1.2.4 reliably parses this model's calls in required-tool
mode. `final_answer` supplies a stopping signal without being forwarded to MCP.
Keeping structured requests and matching call IDs preserves conversation
meaning; removing their duplicate raw representation prevents repeated calls.
For a flight answer, the host also checks for a returned flight number,
departure, duration, INR price, and the fictional-fare disclosure. It inserts
missing fields from the first structured flight result rather than paying for
another slow inference turn. The turn cap bounds a confused or repeatedly
failing model.

## Run the local agent

```powershell
.\workshop.ps1 agent "Find a flight from Bengaluru to Kochi and tell me what to pack."
```

You should see tool-call lines and a grounded answer. Flight fares are fictional
and in INR. Model prose and call order can vary.

Try a single-tool question:

```powershell
.\workshop.ps1 agent "What is the weather in Pune?"
```

Then ask for an unsupported city. The host sends actionable tool errors back to
the model so it can correct the request or explain the supported set.

## Check three code boundaries

Open `src/solution/agent_raw.py` and identify:

1. the property that moves an MCP input schema into a model tool definition
2. the branch between successful structured results and text errors
3. the `MAX_TURNS` limit that stops a model which never finishes

Run the deterministic checks:

```powershell
.\workshop.ps1 test
```
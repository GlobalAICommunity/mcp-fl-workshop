---
id: browser-app
title: Reuse the loop in a local browser
order: 1
estimatedMinutes: 15
---

## Keep one agent core

`src/solution/web.py` imports `run` from the handwritten agent. Its Starlette API
endpoint validates a question, records tool-call events for presentation, and
delegates all orchestration:

```python
tools: list[dict] = []
answer = await run(
    question,
    on_tool_call=lambda name, arguments: tools.append(
        {"name": name, "arguments": arguments}
    ),
)
return JSONResponse({"answer": answer, "tools": tools})
```

The CLI and browser therefore share model loading, discovery, tool execution,
error recovery, and turn limits.

## Run the site

```powershell
.\workshop.ps1 web
```

Open <http://127.0.0.1:7932> and submit:

`What is the weather in Pune?`

The tool label shows the model's MCP request. Exact prose can vary, but the
answer should use deterministic tool results. If time remains, try the slower
multi-tool question `Find a flight from Bengaluru to Kochi and tell me what to
pack.`, or ask `Can you plan a trip to Atlantis?` to confirm that unsupported
destinations do not gain invented data.

The browser sends only a local JSON question to `/api/chat`. It never receives
model files or permission to call arbitrary MCP methods.

## Change the interface, not the loop

In `src/solution/web.py`, change the input placeholder to name another supported
Indian city. Restart the server and confirm the visible text changed while the
agent code stayed untouched.

In production, the HTTP boundary would also authenticate the user, apply an
overall timeout and rate limit, attach a request ID, and filter error details.
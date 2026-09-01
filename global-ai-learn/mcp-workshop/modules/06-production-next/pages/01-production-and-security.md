---
id: production-and-security
title: Bound and authorize production tools
order: 1
estimatedMinutes: 13
---

## Change the controls with the consequences

The lab uses local stdio, fictional data, and read-only behavior. A real service
may use Streamable HTTP, real credentials, and actions with financial or data
impact.

For every production tool:

1. validate arguments at the server boundary
2. authenticate the caller and authorize the exact operation and resource
3. use narrow, preferably per-user credentials
4. constrain paths, queries, result counts, cost, and execution time
5. require human approval for destructive, external, or expensive actions
6. make retries idempotent where possible
7. log actor, tool, outcome, latency, and request ID without logging secrets

A generated schema checks shape. It does not prove that an action is allowed.

## Treat all model context as untrusted

Prompt injection can arrive through user text, tool descriptions, resources, or
tool results. Connect only trusted servers and never delegate authorization to
the model.

Local model execution improves data locality but does not make tool execution
safe. The confused-deputy problem still exists if a server acts with broader
credentials than its caller.

## Run approval through the protocol

The workshop includes a fictional action that never reaches a booking system:

```powershell
.\workshop.ps1 approval
```

Choose yes, no, or cancel. On the first call, `hold_flight` returns an
`InputRequiredResult` containing an `ElicitRequest`. The FastMCP client uses its
`elicitation_handler` to present the choice, then reissues the tool call with
the response. The server reads `ctx.input_responses` and returns a terminal
result. A two-round limit prevents an infinite exchange.

This is host-mediated consent, not model self-approval. Decline and cancel both
leave the action untouched. Form elicitation must never collect secrets such as
passwords, payment details, or tokens.

## Bound the context

Large tool output consumes model context and creates another injection surface.
Return filtered, structured, paginated results instead of unbounded prose or
complete data stores.

For stdio, keep stdout exclusively for MCP messages and send diagnostics to
stderr or a logging sink.

## Compare Streamable HTTP

After the event, you can run a copy of the server on loopback with:

```python
mcp.run(transport="http", host="127.0.0.1", port=8000)
```

A client can then connect to `http://127.0.0.1:8000/mcp`. Tool contracts do not
change when the transport changes. Keep this experiment on loopback. A network
deployment also needs TLS, authentication, per-operation authorization, origin
validation, rate limits, and network controls.

## Extend the lab safely

Choose one low-risk India travel capability, such as a deterministic rail
duration or packing checklist. Give it a narrow schema, bounded output, and
tests for a valid call plus an actionable error.

You now have the complete architecture: FastMCP server, FastMCP client, Foundry
Local agent loop, and browser host. Complete the final assessment.
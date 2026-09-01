# Review production controls

**Time: 13 minutes**

The workshop is intentionally local, deterministic, and low privilege. A real
MCP deployment changes the transport and the risk profile, but not the core
client/server contract.

## From lab to service

| Lab choice | Production decision |
|---|---|
| Local stdio subprocess | Stdio for local hosts or Streamable HTTP for remote clients |
| No user identity | OAuth and per-operation authorization |
| Fictional in-memory data | Narrow service credentials and audited data access |
| At most five flights | Pagination, output limits, and context budgets |
| Read-only examples | Approval gates for destructive or costly actions |
| One local user | Rate limits, timeouts, cancellation, and tenant isolation |

Do not expose a stdio server to the network by wrapping it in an unauthenticated
HTTP endpoint. Choose the remote transport deliberately and authenticate both
the caller and the operation.

## Treat model requests as untrusted input

A schema checks shape, not permission or intent. For every tool:

1. validate arguments at the server boundary
2. authorize the current user for the specific action and resource
3. constrain paths, queries, result counts, and execution time
4. require human approval before irreversible or expensive work
5. return actionable errors without leaking secrets
6. record tool name, actor, outcome, latency, and request ID for audit

Prompt injection can arrive in user text, tool descriptions, resource content,
or tool results. Connect only trusted servers, keep credentials narrow, and do
not rely on a model to enforce access control.

Running the model locally improves data locality. It does not make tool calls
safe by itself.

## Run a modern approval flow

`src/solution/approval_demo.py` places no real booking. It demonstrates the
MCP `2026-07-28` guard flow for an action that would need consent:

```powershell
.\workshop.ps1 approval
```

Choose yes, no, or cancel. On the first call, `hold_flight` returns an
`InputRequiredResult` containing an `ElicitRequest`. The FastMCP client presents
that request through its `elicitation_handler`, then reissues the original tool
call with the response. The tool reads `ctx.input_responses` and returns a final
result. `input_required_max_rounds=2` prevents an accidental infinite exchange.

This is different from asking the model to confirm. The host presents the
choice to the user and transports the result. Decline and cancel both leave the
fictional action untouched. Never collect passwords, payment details, tokens,
or other secrets through form elicitation.

## Keep context bounded

Tool output consumes the model's context window. Prefer structured, filtered,
paginated results over large prose dumps. A tool that returns an entire database
can be both expensive and an injection channel.

## Preserve the protocol channel

For stdio, stdout carries MCP messages. Send diagnostics to stderr or structured
logs. For remote servers, avoid logging tokens, secrets, complete prompts, or
sensitive tool results.

## Optional extension: Streamable HTTP

Stdio is the right event default because it has no listening port. To study the
remote transport after the workshop, run a copy of the server on loopback:

```python
mcp.run(transport="http", host="127.0.0.1", port=8000)
```

Then connect a client to `http://127.0.0.1:8000/mcp`. This changes transport,
not tool schemas. Keep this extension on loopback for the lab. Before binding to
a network interface, add TLS, authentication, per-operation authorization,
origin validation, rate limits, and deployment-specific network controls.

## Your next useful extension

Add one low-risk, India-focused capability to the reference server, such as:

- rail journey duration between a fixed set of cities
- a packing checklist based on weather and trip length
- a destination resource with accessibility notes

Give it a narrow schema, deterministic sample data, bounded output, and a test
for both a valid request and a recoverable error.

## Close

You built and inspected all four layers: a FastMCP server, an MCP client, a
Foundry Local tool-calling loop, and a browser host. Complete the knowledge check
while the distinctions among those layers are fresh.
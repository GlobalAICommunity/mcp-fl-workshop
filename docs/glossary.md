# Glossary

## Agent

A host-side loop that lets a model request tools, executes approved requests,
adds results to the conversation, and repeats until the model answers or a limit
is reached.

## Host

The application the user interacts with. It owns the model conversation,
permissions, MCP clients, tool execution policy, and user interface. The CLI and
browser app are hosts in this workshop.

## Client

One MCP connection from a host to a server. The FastMCP `Client` in the lab
starts and communicates with the travel server.

## Server

A program that publishes named capabilities through MCP. The Bharat Travel Desk
is a local stdio server.

## Tool

A typed capability the model may request, such as `get_weather`. A tool has a
name, description, JSON input schema, and result. The host decides whether a
request is allowed and performs the call through an MCP client.

## Resource

Reference context selected by the application and identified by a URI, such as
`travel://destinations`. A resource is not called autonomously by the model.

## Prompt

A reusable workflow selected deliberately by the user, such as `plan_a_trip`.

## Tool calling

A model feature where the host supplies function definitions and the model can
return a structured request instead of a final prose answer. The model asks; it
does not execute the function itself.

## Structured output

Machine-readable tool data in `structuredContent`, optionally described by an
output schema. Returning a Pydantic model lets FastMCP validate and expose this
shape while also providing text content for models.

## JSON Schema

The standard vocabulary MCP uses to describe tool inputs and structured
outputs. Python annotations and Pydantic metadata can generate these schemas.

## JSON-RPC 2.0

The request and response envelope beneath MCP. Requests include `jsonrpc`, `id`,
`method`, and `params`. Run `workshop.ps1 raw` to see one without a client SDK.

## Transport

The mechanism that carries MCP messages. This workshop uses stdio. Remote
systems commonly use Streamable HTTP.

## stdio

A local transport where the host starts a server subprocess and exchanges MCP
messages through stdin and stdout. Server diagnostics must not be printed to
stdout because it is the protocol channel.

## Streamable HTTP

The MCP transport for remote clients and servers. A production deployment also
needs authentication, authorization, limits, and operational controls.

## `_meta`

Per-request metadata used by protocol revision `2026-07-28` for protocol
version, client information, capabilities, and related namespaced data.

## `server/discover`

The request that asks a `2026-07-28` server to describe its identity and
capabilities. The raw workshop helper uses it by default.

## Protocol revision

An MCP compatibility version written as a date. This workshop is pinned to
`2026-07-28` and verifies the negotiated value at runtime.

## FastMCP

The Python framework used for both the server and client in this workshop.
FastMCP 4.0.0 supplies decorators, schema generation, transport management, and
ergonomic result objects while speaking MCP on the wire.

## Foundry Local

An on-device model runtime and SDK. The workshop uses the WinML Python package,
loads a model from the local catalog and cache, and calls its native chat client
without a cloud endpoint.

## Model alias

A hardware-independent catalog name such as `qwen3.5-0.8b`. This workshop resolves
the alias and explicitly selects its generic CPU variant for VM portability.

## Prompt injection

Instructions hidden in content a model reads, including user input, tool
descriptions, resources, and tool results. Local execution does not remove this
risk.

## Confused deputy

A failure where a server uses its stronger credentials to perform an action for
a caller who should not be allowed to do it. Per-user authorization and narrow
credentials reduce this risk.
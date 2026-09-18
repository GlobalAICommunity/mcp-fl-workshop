### Access and Credentials

| Item | Detail |
| :--- | :----- |
| User | +++@lab.VirtualMachine(Workstation1).Username+++ |
| Password | +++@lab.VirtualMachine(Workstation1).Password+++ |
|  |  |

Build MCP Agents Locally


| Lesson | Time |
| ------ | ---: |
|  [1. Check the offline VM](#lesson-1-check-the-offline-vm) | 5 minutes |
|  [2. Understand MCP](#lesson-2-understand-mcp) | 10 minutes |
|  [3. Build a FastMCP server](#lesson-3-build-a-fastmcp-server) | 20 minutes |
|  [4. Run a client and agent loop](#lesson-4-run-a-client-and-agent-loop) | 25 minutes |
|  [5. Use the browser app](#lesson-5-use-the-browser-app) | 10 minutes |
|  [6. Review production controls](#lesson-6-review-production-controls) | 13 minutes |

## Lesson 1: Check the Offline VM

**Time: 5 minutes**

This workshop starts from a prepared Windows VM. The repository, Python virtual
environment, Foundry Local runtime, and tool-capable CPU model are already
present. 

### 1. Open the Workshop Folder

Open the repository MCP-Workshop in VS Code. Then open a PowerShell terminal with
**Terminal > New Terminal**.

Confirm the terminal is at the repository root. It must contain
[workshop.ps1](workshop.ps1), [requirements-lock.txt](requirements-lock.txt),
**docs**, and **src**:

```powershell
Get-ChildItem
```

all workshop commands assume this location.

### 2. If PowerShell Blocks the Script

Allow local scripts to be executed. 

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\workshop.ps1 check
```
### 3. Run the Offline Check

```powershell
.\workshop.ps1 check
```

the check does not download anything. It verifies:

- Python 3.11 or newer.
- FastMCP 4.0.0 and Foundry Local SDK 1.2.4 in **.venv**.
- The FastMCP server and protocol negotiation.
- The browser application import.
- A cached **qwen3.5-0.8b** model that can emit a tool call.

A ready image ends with output similar to:

```text
[  ok  ] Python version - 3.11
[  ok  ] Virtualenv - FastMCP 4.0.0, Foundry Local SDK 1.2.4, all direct pins match
[  ok  ] MCP server - 4 tools, protocol 2026-07-28, city Pune
[  ok  ] Browser app - ready
[  ok  ] Foundry Local model - qwen3.5-0.8b loaded from cache and emitted get_weather

All good - you are ready for the offline workshop.
```

the first model load can take a little longer than later calls.


### 4. If Any Check Fails

Do not install packages or download a model during the event. Record any issues on the provided repo as issues. The repo is available at:
!IMAGE[qrcode-mcp.png](instructions358450/qrcode-mcp.png)


### Checkpoint

You are ready when all five checks show **[ ok ]** while the VM is offline.
Continue to Lesson 2.

======

## Lesson 2: Understand MCP

**Time: 10 minutes**

The Model Context Protocol is a contract between applications that host models
and servers that expose useful context or actions. It standardizes discovery,
schemas, requests, results, and errors. It does not choose a model or turn a
program into an agent by itself.

With your environment checked, you can inspect that contract before adding
model-driven behavior. The raw helper and SDK client show the same protocol
from two different levels of abstraction.

### The Integration Problem

Without a shared protocol, each of $M$ model hosts needs a custom adapter for
each of $N$ systems. That produces roughly $M \\times N$ integrations.

With MCP, hosts implement the client side and systems implement the server side.
The shape becomes approximately $M + N$.

!IMAGE[MCP architecture: the host connects to Foundry Local and a FastMCP client, which exchanges MCP messages with the server exposing travel functions and data](instructions358450/skillable-1.png)

in this workshop:

- The CLI or browser application is the **host**.
- **fastmcp.Client** owns the MCP **client** connection.
    - [src/solution/travel_server.py](src/solution/travel_server.py) is the MCP **server**.
- Foundry Local runs the **model**.

The model never talks directly to the server. The host discovers tools, gives
their schemas to the model, executes approved requests through the client, and
returns results to the model.

### The Three Server Primitives

| Primitive | Usually selected by | Purpose | Workshop example |
| --------- | ------------------- | ------- | ---------------- |
| Tool | Model | Perform an action or calculation | **get_weather** |
| Resource | Application | Read reference context | **travel://destinations** |
| Prompt | User | Start a reusable workflow | **plan_a_trip** |

The controlling party is the important distinction. A resource is not merely a
read-only tool, and a prompt is not a hidden system instruction.

### Transport and Messages

The lab uses **stdio**. FastMCP starts the Python server as a child process and
sends one JSON-RPC message per line through stdin and stdout. There are no ports
or credentials to configure.

Stdout is therefore part of the protocol. A stdio server must send diagnostics
to stderr or a logger, not with an ordinary **print()** call.

FastMCP 4.0.0 speaks MCP revision **2026-07-28**. Requests carry protocol and
client details in **_meta**, and **server/discover** describes server capabilities.
FastMCP handles that envelope for normal client code.

The revision identifies the protocol grammar; discovery identifies what this
particular peer can do. A client must inspect negotiated capabilities before it
uses optional features such as elicitation. Matching version strings alone do
not prove that a server or client implements every optional capability.

### See the Wire

Run the raw protocol helper:

```powershell
.\workshop.ps1 raw
```

the helper starts the reference server and sends a **server/discover** JSON-RPC
request without using **fastmcp.Client**. Find these fields in the output:

- **jsonrpc: "2.0"**.
- Request **id**.
- Method **server/discover**.
- **_meta** protocol version and client information.
- The server identity and advertised capabilities in the result.

Now compare that with the SDK-driven client:

```powershell
.\workshop.ps1 client
```

the client performs discovery, calls tools, reads a resource, and gets a prompt.
The protocol is the same; FastMCP removes the envelope bookkeeping.

### Checkpoint

You should be able to explain why the model, host, client, and server are four
different roles, and who controls tools, resources, and prompts.

Continue to Lesson 3.
======

## Lesson 3: Build a FastMCP Server

**Time: 20 minutes**

You will create a compact MCP server with typed tools, structured output, a
resource, and a prompt. Later modules use the completed reference server so the
whole room can stay together.

This exercise connects the protocol primitives from Lesson 2 to ordinary
Python functions. You will inspect both a successful result and a recoverable
error before moving on to the client.

### 1. Create the Learner File

Run this from the repository root. Run the file-creation command only for a
new exercise file; **-Force** can overwrite an existing file:

```powershell
New-Item -ItemType Directory -Force src\workshop | Out-Null
New-Item -ItemType File -Force src\workshop\travel_server.py | Out-Null
```

open **src/workshop/travel_server.py** and add:

```python
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "My Bharat Travel Desk",
    instructions="Offline fictional India travel data.",
)

WEATHER = {
    "kochi": (31, "humid"),
    "pune": (27, "clear"),
    "varanasi": (29, "hazy"),
}


class Weather(BaseModel):
    city: str
    temperature_c: int
    condition: str


@mcp.tool
def list_destinations() -> list[str]:
    """List supported cities."""
    return sorted(WEATHER)


@mcp.tool
def get_weather(
    city: Annotated[str, Field(description="Supported city name.")],
) -> Weather:
    """Get today's fictional weather."""
    key = city.strip().lower()
    if key not in WEATHER:
        raise ValueError(f"Unknown city {city!r}. Try: {', '.join(sorted(WEATHER))}.")
    temperature, condition = WEATHER[key]
    return Weather(
        city=key.title(),
        temperature_c=temperature,
        condition=condition,
    )


@mcp.resource("travel://destinations")
def destinations() -> str:
    """A short destination catalogue selected by the application."""
    return "Supported cities: " + ", ".join(city.title() for city in sorted(WEATHER))


@mcp.prompt
def plan_a_trip(city: str, nights: int = 3) -> str:
    """Create a reusable trip-planning request selected by the user."""
    return f"Plan {nights} nights in {city}. Check the weather before suggesting what to pack."


if __name__ == "__main__":
    mcp.run()
```

### 2. Understand What FastMCP Generated

**FastMCP** reads ordinary Python information and publishes MCP definitions:

| Python feature | MCP effect |
| -------------- | ---------- |
| Function name | Tool or prompt name |
| Docstring | Description shown to clients and models |
| Type annotation | JSON Schema field type |
| **Field(...)** | Description and validation metadata |
| Pydantic return model | Output schema and structured content |
| Decorator | Primitive registration |

Descriptions influence model behavior. For a small local model, keep each one
short and discriminative: say what makes the tool different, and leave rules to
types and validation. Repeated prose increases every model request. Type
validation is useful, but it is not authorization.

### 3. Compile the Server

```powershell
.\.venv\Scripts\python -m py_compile src\workshop\travel_server.py
```

no output means the file compiled.

### 4. Discover Your Server

Use the raw helper and point it at your file:

```powershell
.\workshop.ps1 raw server/discover '{}' --server src\workshop\travel_server.py
```

then call the weather tool:

```powershell
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Pune"}}' --server src\workshop\travel_server.py
```

the result includes human-readable content and structured fields derived from
**Weather**.

Try an unsupported city:

```powershell
.\workshop.ps1 raw tools/call '{"name":"get_weather","arguments":{"city":"Atlantis"}}' --server src\workshop\travel_server.py
```

the failure is returned as a tool result rather than crashing the handler. An
agent could use the supported-city hint to try again; this one-shot raw helper
then exits normally after receiving the response.

### 5. Compare the Complete Server

The reference implementation adds deterministic forecasts, fictional flights
in INR, parameter constraints, and ten Indian destinations. Open
[src/solution/travel_server.py](src/solution/travel_server.py), then run:

```powershell
.\workshop.ps1 client
```

notice that FastMCP 4 list methods return Python lists directly and
**call_tool()** raises for tool errors by default. The reference client passes
**raise_on_error=False** when it intentionally demonstrates recoverable failure.

### Checkpoint

You have exposed tools, a resource, and a prompt from normal typed Python and
observed a successful structured result plus a recoverable error.

Continue to Lesson 4.

======

## Lesson 4: Run a Client and Agent Loop

**Time: 25 minutes**

An MCP client is useful without a model. An agent appears only when a host adds
a model, gives it tool schemas, executes requested tools, and repeats. This
module makes that boundary visible.

You will first run the supplied client, then inspect the local model connection
and the handwritten loop. These use the reference server, so they do not depend
on completing your learner server.

**No code changes are required in Lesson 4.** Run the supplied programs and
find the excerpts below in the solution files. Do not paste them into your
learner server or run them separately. Each Python block is an exact excerpt;
only its surrounding indentation is removed where needed for readability.
Use the named functions and calls to locate code rather than fixed line numbers.

### Part A: Call MCP Without a Model

Run the completed client:

```powershell
.\workshop.ps1 client
```

it starts [src/solution/travel_server.py](src/solution/travel_server.py) over
stdio and demonstrates five ordinary client operations:

1. List tools.
2. Call **get_weather** for Pune.
3. Receive a recoverable error for an unknown city.
4. Read **travel://destinations**.
5. Get the **plan_a_trip** prompt for Kochi.

Open [src/solution/mcp_client.py](src/solution/mcp_client.py). Find **SERVER**
and the **server_transport()** helper, which returns this trusted local **Path**:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find:** module-level **SERVER** and **server_transport()**.

```python
SERVER = REPO_ROOT / "src" / "solution" / "travel_server.py"


def server_transport() -> Path:
    """Return the trusted local script FastMCP should launch over stdio."""
    return SERVER
```

Find the start of **main()**. It opens the client using that helper:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find in:** **main()** at **Client(server_transport())**.

```python
async def main() -> None:
    async with Client(server_transport()) as client:
        print(f"Connected. Protocol revision: {client.protocol_version}\n")
```

fastmcp 4 infers a Python stdio transport from the path. A bare string ending in
**.py** is deprecated because it is ambiguous.

Inside **main()**, find **list_tools()** and compare the printed names with the
terminal output:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find in:** **main()** at **client.list_tools()**.

```python
tools = await client.list_tools()
print("Tools:")
for tool in tools:
    print(f"  - {tool.name}: {tool.description}")
print()
```

Next, find **list_resources()** and **read_resource()**. List and read methods
return lists directly in FastMCP 4:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find in:** **main()** at **client.list_resources()**.

```python
resources = await client.list_resources()
print("Resources:", [str(resource.uri) for resource in resources])
catalog = await client.read_resource("travel://destinations")
print(catalog[0].text)
print()
```

Find **list_prompts()** immediately below the resource section:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find in:** **main()** at **client.list_prompts()**.

```python
prompts = await client.list_prompts()
print("Prompts:", [prompt.name for prompt in prompts])
prompt = await client.get_prompt(
    "plan_a_trip", {"city": "Kochi", "nights": "4"}
)
print(json.dumps(prompt.messages[0].content.text, indent=2))
```

**call_tool()** raises on a tool error by default. Use **raise_on_error=False**
only when the caller is prepared to inspect the error and recover. Find the
Atlantis call and its **oops** result:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find in:** **main()** at **oops = await client.call_tool(...)**.

```python
oops = await client.call_tool(
    "get_weather", {"city": "Atlantis"}, raise_on_error=False
)
print("get_weather('Atlantis')")
print("  is_error:", oops.is_error)
print("  text    :", oops.content[0].text)
print()
```

Successful typed tools provide **structured_content**. Find the earlier Pune
call, which prints both the structured object and its text representation:

**File:** [src/solution/mcp_client.py](src/solution/mcp_client.py)  
**Find in:** **main()** at **weather = await client.call_tool(...)**.

```python
weather = await client.call_tool("get_weather", {"city": "Pune"})
print("get_weather('Pune')")
print("  structured:", weather.structured_content)
print("  text      :", weather.content[0].text)
print()
```

use the structured object for application logic. Text content remains useful
for display, recoverable errors, and compatibility with servers that do not
publish structured output.

There is no model or API key in this program. Retrieving an MCP prompt is not a
model call: MCP is working before any agent behavior is added.

### Part B: Connect the Local Model

[src/model_config.py](src/model_config.py) asks the Foundry Local singleton for
the hardware-independent alias **qwen3.5-0.8b**, then explicitly selects the
highest-priority CPU variant exposed by the catalog.
It rejects unknown, accelerator-only, non-tool-capable, or uncached models. If needed,
it loads the cached model and returns its native chat client.

The image builder performed the download earlier. Open
[src/solution/agent_raw.py](src/solution/agent_raw.py) and find the start of
**run()**. It uses an injected client for tests or obtains the cached model's client:

**File:** [src/solution/agent_raw.py](src/solution/agent_raw.py)  
**Find in:** **run()** at **llm = chat_client**.

```python
llm = chat_client
if llm is None:
    llm = get_local_model().client
llm.settings.tool_choice = {"type": "required"}
```

the Foundry Local chat call is synchronous, while the MCP client is asynchronous.
Inside the turn loop's **try** block, find **asyncio.to_thread**. It keeps inference
from blocking the event loop:

**File:** [src/solution/agent_raw.py](src/solution/agent_raw.py)  
**Find in:** **run()** at **response = await asyncio.to_thread(...)**.

```python
response = await asyncio.to_thread(
    llm.complete_chat,
    messages,
    tools,
)
```

no local HTTP endpoint is required.

Foundry Local SDK 1.2.4 returns structured calls for this model when
**tool_choice** is **required**. The host first filters the four MCP travel tools
to those relevant to the question, then adds one host-only **final_answer**
function. Ambiguous questions retain all tools. The model chooses a travel tool
while it needs data and calls **final_answer** when it is ready to stop. That last
function is handled by the host and is never sent to the MCP server.

### The Schema Adapter

MCP and model tool calling both use JSON Schema, but their outer objects differ.
The adapter in [src/solution/agent_raw.py](src/solution/agent_raw.py) also strips
generated schema labels that do not help the model choose arguments:

**File:** [src/solution/agent_raw.py](src/solution/agent_raw.py)  
**Find:** **mcp_tools_to_openai()**.

```python
def compact_schema(value):
    if isinstance(value, dict):
        return {
            key: compact_schema(item)
            for key, item in value.items()
            if key not in {"title", "additionalProperties"}
        }
    if isinstance(value, list):
        return [compact_schema(item) for item in value]
    return value


def mcp_tools_to_openai(tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": compact_schema(tool.input_schema),
            },
        }
        for tool in tools
    ]
```

the Python property is **input_schema**; the MCP JSON field on the wire is
**inputSchema**. MCP discovery still returns the complete schema. Compaction is
a host-side optimization applied only to the copy sent to the model.

### Route Only Relevant Tools

Before the turn loop, **tools_for_question()** uses small keyword groups to keep
likely tools plus **final_answer**. For example, a weather question does not pay
the token cost of the flight schema. If no hint matches, it keeps every tool so
unusual wording remains recoverable.

### The Complete Loop

!IMAGE [Agent loop: send the user question, messages, and tools to Foundry Local; return a final answer or execute travel tools through FastMCP, append results with matching call IDs, and repeat](instructions358450/skillable-2.png)
open the **run()** function and find each arrow in code. These details prevent
subtle failures:

- Keep the assistant turn and its structured tool requests.
- Omit duplicate raw **<tool_call>** markup when structured calls are present.
- Attach every tool result to the matching **tool_call_id**.
- Unwrap a sole **result** envelope and serialize the smaller structured value
    for the model instead of parsing JSON back out of a text block.
- If a flight answer omits required fields, insert them from the first
    structured flight result instead of starting another slow model turn.
- Cap the loop with **MAX_TURNS**.

The loop also gives malformed JSON and MCP tool errors back to the model as
text. That lets the next turn correct a request instead of crashing the host.

### Run a Multi-Tool Question

```powershell
.\workshop.ps1 agent "Find a flight from Bengaluru to Kochi and tell me what to pack."
```

you should see one or more **-> calling ...** lines followed by a concise answer.
Flight fares are fictional and shown in INR. Exact wording and call order can
vary because the model is generative.

Try a smaller request:

```powershell
.\workshop.ps1 agent "What is the weather in Pune?"
```

then ask for an unsupported city. Inspect whether the model reads the error,
calls **list_destinations**, or explains the supported set.

### Guided Code Checkpoints

Open [src/solution/agent_raw.py](src/solution/agent_raw.py) and find these three
boundaries:

1. **Schema check:** Identify the one property that moves an MCP input schema
    into the model's function definition.
2. **Result check:** Identify where successful structured results and text errors
    take different paths.
3. **Safety check:** Find **MAX_TURNS** and the return statement after the loop.
    Predict what would happen if the limit were **2** and the model never stopped.
    Leave the code unchanged at **6**.

Run the deterministic checks after inspecting the loop:

```powershell
.\workshop.ps1 test
```

### Checkpoint

You can now separate three mechanisms:

- MCP publishes and executes capabilities.
- Foundry Local chooses a travel tool or the host-only stopping function.
- The host loop preserves conversation state and connects the two.

Continue to Lesson 5.

======

## Lesson 5: Use the Browser App

**Time: 10 minutes**

The browser is another interface over the same **run()** function. It does not
contain a second agent implementation and it does not connect directly to the
MCP server or model.

You will follow the HTTP request into the existing loop, try a question, and
make a presentation-only change. The model and MCP behavior remain the same as
in the CLI exercise.

### 1. Follow the Request Path

Open [src/solution/web.py](src/solution/web.py). The Starlette application has
two routes:

```python
app = Starlette(
    routes=[
        Route("/", homepage),
        Route("/api/chat", chat, methods=["POST"]),
    ]
)
```

the API endpoint validates the question, records tool-call events, and delegates
to the existing loop:

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

the callback changes presentation only. Tool discovery, Foundry Local calls,
MCP execution, result matching, and turn limits remain in
[src/solution/agent_raw.py](src/solution/agent_raw.py).

### 2. Start the Local Site

```powershell
.\workshop.ps1 web
```

open [http://127.0.0.1:7932](http://127.0.0.1:7932). Keep the terminal visible for errors and stop the
server with **Ctrl+C** when finished.

### 3. Exercise the Agent

Submit this question:

**What is the weather in Pune?**

The orange label shows which MCP tool the model requested. If time remains, try
one slower extension:

!IMAGE[bBharat Travel Desk showing a Pune weather answer and the orange get_weather tool trace.](instructions358450/browser-tool-trace.png)

*Expected browser state. Exact prose and weather values can vary by workshopdate; look for the orange **get_weather({"city":"Pune"})** trace beneath a groundedanswer.*

### 4. Inspect the HTTP Boundary

The browser sends only this local request:

```json
{"question":"What is the weather in Pune?"}
```

the response has an answer and a presentation-friendly tool trace:

```json
{
  "answer": "...",
  "tools": [
    {"name": "get_weather", "arguments": {"city": "Pune"}}
  ]
}
```

the browser never receives model files, server credentials, or permission to
execute arbitrary MCP methods. In a production app, this HTTP boundary is also
where you would authenticate the user, enforce request limits, attach a request
ID, and apply an overall timeout.

### 5. Make One Visible Change

In [src/solution/web.py](src/solution/web.py), change the input placeholder to
mention another supported Indian city. Stop the server, run
**.\workshop.ps1 web** again, and confirm the browser shows your text without
changing the agent loop.

### Checkpoint

You have used one agent core from a CLI and a browser and observed the model's
MCP tool choices without exposing internal reasoning.

Continue to Lesson 6.

======

## Lesson 6: Review Production Controls

**Time: 13 minutes**

The workshop is intentionally local, deterministic, and low privilege. A real
MCP deployment changes the transport and the risk profile, but not the core
client/server contract.

Now that you have seen the complete request path, identify which boundaries
need validation, authorization, and user approval. The supplied approval demo
lets you inspect consent without making a real booking.

### From Lab to Service

| Lab choice | Production decision |
| ---------- | ------------------- |
| Local stdio subprocess | Stdio for local hosts or Streamable HTTP for remote clients |
| No user identity | OAuth and per-operation authorization |
| Fictional in-memory data | Narrow service credentials and audited data access |
| At most five flights | Pagination, output limits, and context budgets |
| Read-only examples | Approval gates for destructive or costly actions |
| One local user | Rate limits, timeouts, cancellation, and tenant isolation |

Do not expose a stdio server to the network by wrapping it in an unauthenticated
HTTP endpoint. Choose the remote transport deliberately and authenticate both
the caller and the operation.

### Treat Model Requests as Untrusted Input

A schema checks shape, not permission or intent. For every tool:

1. Validate arguments at the server boundary.
2. Authorize the current user for the specific action and resource.
3. Constrain paths, queries, result counts, and execution time.
4. Require human approval before irreversible or expensive work.
5. Return actionable errors without leaking secrets.
6. Record tool name, actor, outcome, latency, and request ID for audit.

Prompt injection can arrive in user text, tool descriptions, resource content,
or tool results. Connect only trusted servers, keep credentials narrow, and do
not rely on a model to enforce access control.

Running the model locally improves data locality. It does not make tool calls
safe by itself.

### Run a Modern Approval Flow

[src/solution/approval_demo.py](src/solution/approval_demo.py) places no real
booking. It demonstrates the MCP **2026-07-28** guard flow for an action that
would need consent:

```powershell
.\workshop.ps1 approval
```

choose yes, no, or cancel. On the first call, **hold_flight** returns an
**InputRequiredResult** containing an **ElicitRequest**. The FastMCP client presents
that request through its **elicitation_handler**, then reissues the original tool
call with the response. The tool reads **ctx.input_responses** and returns a final
result. **input_required_max_rounds=2** prevents an accidental infinite exchange.

This is different from asking the model to confirm. The host presents the
choice to the user and transports the result. Decline and cancel both leave the
fictional action untouched. Never collect passwords, payment details, tokens,
or other secrets through form elicitation.

### Keep Context Bounded

Tool output consumes the model's context window. Prefer structured, filtered,
paginated results over large prose dumps. A tool that returns an entire database
can be both expensive and an injection channel.

### Preserve the Protocol Channel

For stdio, stdout carries MCP messages. Send diagnostics to stderr or structured
logs. For remote servers, avoid logging tokens, secrets, complete prompts, or
sensitive tool results.

### Optional Extension: Streamable HTTP

Stdio is the right event default because it has no listening port. To study the
remote transport after the workshop, run a copy of the server on loopback:

```python
mcp.run(transport="http", host="127.0.0.1", port=8000)
```

then connect a client to **http://127.0.0.1:8000/mcp**. This changes transport,
not tool schemas. Keep this extension on loopback for the lab. Before binding to
a network interface, add TLS, authentication, per-operation authorization,
origin validation, rate limits, and deployment-specific network controls.

### Your Next Useful Extension

Add one low-risk, India-focused capability to the reference server, such as:

- Rail journey duration between a fixed set of cities.
- A packing checklist based on weather and trip length.
- A destination resource with accessibility notes.

Give it a narrow schema, deterministic sample data, bounded output, and a test
for both a valid request and a recoverable error.

======

### Close

You built and inspected all four layers: a FastMCP server, an MCP client, a
Foundry Local tool-calling loop, and a browser host. Complete the session's
knowledge check while the distinctions among those layers are fresh.

You can complete this lab at
!IMAGE[qrcode-mcp.png](instructions358450/qrcode-mcp.png)

If you have any feedback on the lab or encounter issues please leave feedback using issues on the repo.
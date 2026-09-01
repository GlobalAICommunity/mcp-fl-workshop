---
schemaVersion: 1
id: mcp-workshop
version: "2.0"
title: Build offline agents with the Model Context Protocol
summary: Build a FastMCP server, connect it to a Foundry Local agent, and use it from a browser on a fully offline Windows VM.
durationMinutes: 90
difficulty: Intermediate
prerequisites:
  - A prebuilt workshop Windows VM
  - Basic Python functions and type hints
learningOutcomes:
  - Explain the roles of an MCP host, client, server, and model
  - Build a FastMCP 4 server with typed tools, a resource, and a prompt
  - Trace a complete tool-calling loop using a cached Foundry Local model
  - Reuse one MCP agent loop from a command line and a browser
  - Run a host-mediated approval with the modern MCP input-required flow
  - Identify authorization, approval, logging, and output controls for production tools
modules: [setup, mcp-basics, build-server, agent-loop, browser, production-next]
---

In this hands-on course, you build and run a fictional India travel assistant
with FastMCP 4.0.0 and Foundry Local. Weather, forecasts, destinations, and INR
flight fares are deterministic lab data, not live booking information.

The repository, Python environment, Foundry Local runtime, and tool-capable
generic CPU variant of `qwen3.5-0.8b` are already installed in the workshop VM.
Every learner exercise runs without a cloud account, API key, download, or
network connection.

The six lesson pages take 83 minutes. Reserve the final 7 minutes for this
course's assessment and close, for a total of 90 minutes.

You write one compact FastMCP server, then use completed reference files for the
client, handwritten agent loop, and browser. This keeps the focus on protocol
boundaries and tool behavior while ensuring the full application runs within the
event session.
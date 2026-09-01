---
id: agent-loop
title: Run a client and agent loop
summary: Call MCP without a model, then trace how Foundry Local tool requests become FastMCP calls and results.
order: 4
pages: [client-and-loop]
questions:
  - id: preserve-tool-turn
    type: single-choice
    prompt: Why must the host preserve the assistant turn's structured tool calls?
    options:
      - id: stateless-model
        text: The next model request needs the tool requests in history so returned results have conversational context
      - id: server-memory
        text: The MCP server stores assistant messages for later retrieval
      - id: schema-refresh
        text: Tool schemas can only be generated from a previous assistant message
    correctOptionIds: [stateless-model]
    explanation: The message list is the model's working conversation state. Preserve structured calls and omit any duplicate raw tool markup before appending their results.
---

Observe MCP as an ordinary application protocol first. Then follow one complete
model, tool, result, and final_answer cycle in the supplied handwritten loop.
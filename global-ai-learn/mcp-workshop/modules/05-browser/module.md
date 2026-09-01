---
id: browser
title: Use the browser app
summary: Reuse the handwritten FastMCP and Foundry Local loop behind a local Starlette interface.
order: 5
pages: [browser-app]
questions:
  - id: shared-loop
    type: single-choice
    prompt: Why does the browser endpoint call the existing run function?
    options:
      - id: consistent-behavior
        text: The CLI and browser share tool discovery, model turns, MCP execution, errors, and limits
      - id: bypass-protocol
        text: Browser requests cannot use an MCP server
      - id: remove-http
        text: Reusing the loop removes the need for an HTTP endpoint
    correctOptionIds: [consistent-behavior]
    explanation: One agent core keeps behavior consistent while each interface handles only its own input and presentation concerns.
---

Run the same local agent from a browser and observe which MCP tools the model
requests without duplicating the orchestration logic.
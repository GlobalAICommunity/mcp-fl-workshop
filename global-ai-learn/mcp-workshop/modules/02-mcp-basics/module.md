---
id: mcp-basics
title: Understand MCP
summary: Separate host, client, server, and model roles, then compare tools, resources, prompts, and transports.
order: 2
pages: [protocol-foundations]
questions:
  - id: primitive-control
    type: multiple-choice
    prompt: Which statements correctly match MCP primitives to the party that usually selects them?
    options:
      - id: model-tools
        text: The model requests tools
      - id: application-resources
        text: The application selects resources
      - id: user-prompts
        text: The user deliberately selects prompts
      - id: model-prompts
        text: The model silently selects every prompt
    correctOptionIds: [model-tools, application-resources, user-prompts]
    explanation: Tools are model-controlled, resources are application-controlled, and prompts are user-controlled.
---

Build the protocol mental model before adding implementation details. The key is
knowing which component owns each decision.
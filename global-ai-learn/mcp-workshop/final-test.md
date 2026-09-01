---
title: Build offline agents with MCP final test
questions:
  - id: final-boundaries
    type: single-choice
    prompt: Which component connects model tool requests to MCP execution?
    options:
      - id: host-loop
        text: The host agent loop
      - id: model-direct
        text: A direct connection from the model to the MCP server
      - id: resource-template
        text: An MCP resource template
    correctOptionIds: [host-loop]
    explanation: The host owns the model conversation and MCP clients, executes approved requests, and returns results to the model.
  - id: final-primitives
    type: multiple-choice
    prompt: Which primitive and controller pairings are correct?
    options:
      - id: tool-model
        text: Tools are requested by the model
      - id: resource-application
        text: Resources are selected by the application
      - id: prompt-user
        text: Prompts are deliberately selected by the user
      - id: resource-model
        text: Resources are always fetched directly by the model
    correctOptionIds: [tool-model, resource-application, prompt-user]
    explanation: The controlling party distinguishes tools, resources, and prompts.
  - id: final-server-schema
    type: multiple-choice
    prompt: Which Python elements can contribute to a FastMCP tool contract?
    options:
      - id: annotations
        text: Type annotations
      - id: pydantic-fields
        text: Pydantic field metadata and constraints
      - id: docstrings
        text: Function docstrings
      - id: stdout-debug
        text: Debug text printed to stdout
    correctOptionIds: [annotations, pydantic-fields, docstrings]
    explanation: Types, field metadata, and descriptions generate schemas and definitions. Stdout is the stdio protocol channel.
  - id: final-error-recovery
    type: true-false
    prompt: A recoverable tool error should explain what was invalid so the model can correct a later request.
    options:
      - id: "true"
        text: "True"
      - id: "false"
        text: "False"
    correctOptionIds: ["true"]
    explanation: Actionable tool results support bounded recovery instead of crashing the host or encouraging guesses.
  - id: final-loop-state
    type: multiple-choice
    prompt: Which practices are required in the handwritten tool loop?
    options:
      - id: preserve-assistant
        text: Preserve assistant turns that contain structured tool calls
      - id: match-call-id
        text: Match each tool result to its request ID
      - id: remove-duplicate-markup
        text: Omit duplicate raw tool-call markup when structured calls are present
      - id: cap-turns
        text: Set a maximum number of turns
      - id: hide-errors
        text: Discard every tool error before the model sees it
    correctOptionIds: [preserve-assistant, match-call-id, remove-duplicate-markup, cap-turns]
    explanation: Structured history, call ID matching, duplicate removal, and a turn cap preserve correctness and bound failures.
  - id: final-offline-ready
    type: single-choice
    prompt: What is the strongest proof that the VM model is ready for the offline lab?
    options:
      - id: emitted-tool-call
        text: The cached model loads with networking disabled and emits the required tool call
      - id: imported-package
        text: The Foundry Local package imports
      - id: cache-folder
        text: A model cache folder exists
    correctOptionIds: [emitted-tool-call]
    explanation: Imports and files are necessary but only real offline inference proves the runtime and model work together.
  - id: final-production
    type: multiple-choice
    prompt: Which controls reduce production MCP risk?
    options:
      - id: per-operation-auth
        text: Per-operation authorization
      - id: bounded-output
        text: Bounded and paginated output
      - id: approval
        text: Human approval for costly or destructive actions
      - id: trust-model
        text: Treat all schema-valid model arguments as authorized
    correctOptionIds: [per-operation-auth, bounded-output, approval]
    explanation: Model-generated arguments remain untrusted. Production systems need authorization, limits, and approval for consequential actions.
---

This seven-question assessment covers the architecture, FastMCP server contract,
offline model readiness, agent-loop state, error recovery, and production
controls. Allow seven minutes, including review.
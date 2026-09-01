---
id: build-server
title: Build a FastMCP server
summary: Publish typed tools, structured output, a resource, a prompt, and actionable errors from ordinary Python.
order: 3
pages: [server-capabilities]
questions:
  - id: generated-contract
    type: multiple-choice
    prompt: Which Python features help FastMCP generate a tool contract?
    options:
      - id: annotations
        text: Parameter and return type annotations
      - id: field-metadata
        text: Pydantic Field descriptions and constraints
      - id: docstring
        text: A precise function docstring
      - id: print-output
        text: Diagnostic text printed to stdout
    correctOptionIds: [annotations, field-metadata, docstring]
    explanation: FastMCP uses types, Pydantic metadata, and descriptions to build schemas and model-facing definitions. Stdout is reserved for the stdio protocol.
---

Create a small India travel server and exercise it at the raw JSON-RPC boundary.
Then compare it with the richer deterministic reference implementation.
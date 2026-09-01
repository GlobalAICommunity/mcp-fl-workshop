---
id: setup
title: Check the offline VM
summary: Verify the prepared Python environment, MCP server, browser app, model cache, and local tool calling.
order: 1
pages: [prepare-environment]
questions:
  - id: offline-readiness
    type: multiple-choice
    prompt: Which results are required before the workshop VM is ready for offline use?
    options:
      - id: pinned-packages
        text: The pinned FastMCP and Foundry Local packages import from the workshop environment
      - id: cached-model
        text: The selected generic CPU model is already cached for the attendee account
      - id: real-tool-call
        text: The local model emits the required get_weather tool call
      - id: cloud-login
        text: The attendee signs in to a cloud model provider
    correctOptionIds: [pinned-packages, cached-model, real-tool-call]
    explanation: Offline readiness requires the pinned runtime, cached assets, and a real tool-call smoke test. No cloud login is part of the workshop.
---

Treat the VM image as the reproducible workshop unit. Attendees verify it but do
not install packages or download models during the event.
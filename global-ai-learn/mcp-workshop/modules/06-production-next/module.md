---
id: production-next
title: Review production controls
summary: Apply authorization, approval, bounded-output, logging, and prompt-injection controls beyond the local lab.
order: 6
pages: [production-and-security]
questions:
  - id: production-controls
    type: multiple-choice
    prompt: Which controls reduce risk when an MCP tool can affect real systems?
    options:
      - id: authorize-operation
        text: Authorize the current user for each operation and resource
      - id: bound-results
        text: Limit execution time and result size
      - id: approve-actions
        text: Require human approval for destructive or costly actions
      - id: trust-schema
        text: Trust arguments whenever they match the generated schema
    correctOptionIds: [authorize-operation, bound-results, approve-actions]
    explanation: Schema validation does not prove permission or intent. Approval must be presented by the host and transported to the tool; it is not a decision delegated to the model.
---

Turn the local architecture into a practical production checklist without
mistaking local model execution for complete application security.
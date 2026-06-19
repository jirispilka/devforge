---
name: devforge-impl-feature-dev
description: devforge implementer adapter — drive the vendored feature-dev engine in implement-only mode against the approved design.md, then write claim.md. Dispatched by the orchestrator; not for direct use.
---

# devforge implementer ← feature-dev (adapter)

Thin wrapper that fills devforge's **implementer** slot with the vendored
`feature-dev` engine. You are dispatched as a subagent on the configured model; you
coordinate only through `.devforge/` files.

## Inputs (read these)
- `.devforge/design.md` — the **approved** spec. This is your source of truth.
- `.devforge/task.md`, `.devforge/validation.md` — context.
- The latest `.devforge/iter-*/review-*.md` and `.devforge/iter-*/final-review-*.md`
  — every reviewer finding you must address this iteration.

## Engine
Follow `.claude/skills/_vendored/feature-dev/feature-dev.md`, **implementation phase
only**:
- **Skip** feature-dev's Discovery, clarifying-questions, and architecture phases —
  devforge already explored, designed (`design.md`), and got **human approval** at the
  design gate. Re-asking or re-designing here is wrong.
- You MAY dispatch the `devforge-code-explorer` and `devforge-code-architect` agents
  for grounding (understanding existing code) — not for redesigning the approach.
- Implement `design.md`. Then address **every** finding from the prior review files:
  apply the smallest fix that resolves each real, proportionate finding (nits
  included). Skip one only if genuinely unnecessary/disproportionate, and record the
  **specific** reason in `claim.md` ("out of scope" alone is not a reason).
- Where two reviewers pulled in opposite directions, implement the reconciliation the
  orchestrator recorded and note it.

## Hard rules
- **Never edit or delete tests to pass.** Trust the oracle.
- Only edit source needed for `design.md` + the findings.

## Output (write this)
`.devforge/iter-N/claim.md` — what you did, what you skipped and the specific reason,
and evidence (files touched, how it satisfies the design). The reviewers never see this
file; it is for the human.

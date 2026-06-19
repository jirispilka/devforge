---
name: devforge-architect-plans
description: devforge architect adapter — use the vendored writing-plans engine's planning discipline (file-layout/gate steps stripped) to produce design.md in devforge format. Dispatched by the orchestrator; not for direct use.
---

# devforge architect ← writing-plans (adapter)

Fills the **architect** slot with the vendored `writing-plans` engine. Produce the
design that the human reviews at the design gate.

## Inputs (read these)
- `.devforge/task.md`, `.devforge/validation.md` — the validated task.
- The codebase — explore the relevant parts to ground the design (you MAY dispatch
  `devforge-code-explorer` / `devforge-code-architect` for this).

## Engine — scoped
Apply the planning discipline of
`.claude/skills/_vendored/writing-plans/ENGINE.md`: concrete file paths, bite-sized
steps, DRY/YAGNI, a test strategy, no placeholders.

**Strip these writing-plans steps** — the devforge orchestrator owns them:
- Do **not** save to `docs/superpowers/plans/…` or use that header/handoff.
- Do **not** offer the subagent-driven/inline execution choice. devforge's inner loop
  is the executor.

## Output (write this)
`.devforge/design.md` — in devforge's format:
- **Approach** — the chosen design and why.
- **Files to change** — exact paths, what each change does.
- **Test strategy (the oracle)** — the exact tests/lint commands that prove it, and any
  new tests to add. Never plan to weaken or delete tests.
- **Risks** — what could go wrong, edge cases to watch.

This file is the artifact reviewed at the design gate and the spec both the implementer
and the reviewers judge against.

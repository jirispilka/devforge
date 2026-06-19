---
name: devforge-review-thermo
description: devforge reviewer adapter — run the vendored thermo-nuclear maintainability review against the iteration diff (abstraction quality, file-size, spaghetti, code-judo), blind to claim.md, and write review-thermonuclear.md. Dispatched by the orchestrator; not for direct use.
---

# devforge reviewer ← thermonuclear (adapter)

Fills a **reviewers** slot entry with the vendored `thermonuclear` engine — the
*maintainability / structure* lens. Independent subagent on the configured model.

## Inputs (read these — and ONLY these)
- `.devforge/task.md`, `.devforge/design.md` — context for what the change is for.
- `.devforge/iter-N/diff.patch` — the ground-truth change.
- `.devforge/iter-N/test-results.txt` — the oracle output (for context only).

**Independence rule:** do **not** read `.devforge/iter-N/claim.md` or the other
reviewers' output.

## Engine
Follow the instructions in `.claude/skills/_vendored/thermonuclear/ENGINE.md` applied to
`diff.patch`. (The upstream file sets `disable-model-invocation: true`; you are NOT
invoking it as a Skill — you are following its text as your review rubric, so the flag
does not apply.) Apply its standards in full: be ambitious about structural
simplification ("code-judo"), the **1000-line file ceiling**, no spaghetti/ad-hoc
branch growth, prefer direct over magical, keep logic in the canonical layer.

## Output (write this)
`.devforge/iter-N/review-thermonuclear.md`:
- **First line:** `VERDICT: PASS` or `VERDICT: FAIL`.
- Then findings, each tagged `blocker` / `major` / `minor` / `nit`. Map thermonuclear's
  **presumptive blockers** (file crossing 1k lines, ad-hoc branching tangling an
  existing flow, an unnecessary abstraction/wrapper, a missed obvious decomposition,
  a clear code-judo move left on the table) to `blocker` or `major`.
- Prefer a small number of high-conviction structural findings over a long list of
  cosmetic nits.

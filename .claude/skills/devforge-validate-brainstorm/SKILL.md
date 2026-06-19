---
name: devforge-validate-brainstorm
description: devforge validate adapter — use the vendored brainstorming engine's clarifying-question discipline (gate/commit steps stripped) plus devforge's issue staleness check, then write task.md and validation.md. Dispatched by the orchestrator; not for direct use.
---

# devforge validate ← brainstorming (adapter)

Fills the **validate** slot with the vendored `brainstorming` engine. Confirm the task
is specific enough to act on and that its premises are still true.

## Inputs (read these)
- The `<task>` argument / issue reference passed by the orchestrator.
- The codebase, and (if the task cites an issue/PR) GitHub via `gh`.

## Engine — scoped
Apply the clarifying-question discipline of
`.claude/skills/_vendored/brainstorming/ENGINE.md`: understand purpose, constraints, and
success criteria; surface genuine ambiguities; prefer narrowing scope over guessing.

**Strip these brainstorming steps** — the devforge orchestrator owns them:
- Do **not** write or commit a separate spec doc to `docs/superpowers/specs/…`.
- Do **not** run brainstorming's own approval gate or transition to writing-plans.
  (devforge's design gate + architect slot do that.)

## devforge staleness check (keep this)
If the task references a GitHub issue (number/URL) or cites specific code locations,
run the claim/staleness check before designing:
1. Fetch + timestamp: `gh issue view <n> --json title,body,createdAt,comments,labels`.
2. Build a claim ledger (code refs, behavioral/causal claims, repro steps).
3. Verify each against current HEAD (grep/Read; `git log --since=<createdAt>`,
   `-S<symbol>`, `--grep="#<n>"`). Mark `VALID | STALE(→corrected) | LIKELY-FIXED |
   UNVERIFIABLE` with evidence.
4. If core claims are STALE or it looks LIKELY-FIXED, STOP and surface to the human with
   a recommendation before designing.

## Output (write these)
- `.devforge/task.md` — the restated task using **corrected, current** references.
- `.devforge/validation.md` — the claim ledger + a one-line verdict (or a short "task is
  clear, no external claims to verify" when not issue-based).

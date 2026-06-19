# devforge configuration

devforge's phases are **slots**. A *slot* is a role defined only by the files it reads
and writes; what *fills* it — which vendored skill, on which model — is config you set in
`.devforge/config.json`. Swap a slot's `use` value and the loop runs a different engine
without any change to the orchestrator. The **oracle** (your project's tests/lint) is the
deterministic ground truth and is **not** a slot.

Every engine is **vendored in this repo** (`.claude/skills/_vendored/`) and run through a
thin adapter (`.claude/skills/devforge-*`). Nothing needs installing — see
[`VENDORED.md`](../VENDORED.md).

## The slots

| Slot | Runs | Reads | Writes | `use` options (default **bold**) | Model |
|------|------|-------|--------|----------------------------------|-------|
| `validate` | once, first | the task / issue, codebase | `task.md`, `validation.md` | **`brainstorming`**, `builtin` | opus |
| `architect` | once, after explore | `task.md`, `validation.md`, codebase | `design.md` | **`writing-plans`**, `builtin` | opus |
| `implementer` | every iteration | `design.md`, prior reviews | source edits, `claim.md` | **`feature-dev`**, `builtin` | opus |
| `reviewers` (list) | every iteration, parallel | `diff.patch`, `test-results.txt`, spec | `review-<use>.md` each | **`staff-review`** + **`thermonuclear`**, `code-review`, `builtin` | sonnet |
| `final_reviewers` (list) | after convergence, parallel | `diff.patch` + working tree, spec | `final-review-<use>.md` each | **`code-review`**, `staff-review`, `thermonuclear` | sonnet |

### What each engine does

- **`brainstorming`** — clarifying-question discipline to pin down purpose/constraints
  (devforge strips its spec-doc/gate steps; keeps the issue staleness check).
- **`writing-plans`** — concrete, file-level plan → `design.md`.
- **`feature-dev`** — codebase-aware implementation (driven implement-only against the
  approved design).
- **`staff-review`** — correctness / edge cases / test coverage.
- **`thermonuclear`** — strict maintainability: abstraction quality, 1k-line file
  ceiling, spaghetti-branch growth, "code-judo" simplification.
- **`code-review`** — multi-agent bug / CLAUDE.md / git-history pass with confidence
  scoring (retargeted from a PR to the iteration diff).
- **`builtin`** — devforge's own inline skeleton step for that phase; no vendored engine.

Each reviewer runs as an independent subagent, **blind to `claim.md` and to the other
reviewers**, so the lenses stay genuinely independent.

## Limits & gate

```json
{ "limits": { "inner_iterations": 3, "final_review_rounds": 2 }, "plan_mode_gate": true }
```

- `inner_iterations` — implement→oracle→reviewers rounds before escalating.
- `final_review_rounds` — how many times a final review may reopen the inner loop.
- `plan_mode_gate` — when true and running interactively in the CLI, the design gate
  uses Claude Code's plan-mode (`ExitPlanMode`) for native approval; otherwise (and
  always on web) it falls back to `/devforge-approve-design`. The marker file is the
  source of truth either way.

## Example configs

### `default`
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers": [
      { "use": "staff-review",  "model": "sonnet" },
      { "use": "thermonuclear", "model": "sonnet" }
    ],
    "final_reviewers": [
      { "use": "code-review",   "model": "sonnet" }
    ]
  },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

### `fast-cheap` — one reviewer, no final pass, fewer rounds
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "haiku" },
    "architect":   { "use": "writing-plans", "model": "sonnet" },
    "implementer": { "use": "feature-dev",   "model": "sonnet" },
    "reviewers": [
      { "use": "staff-review", "model": "haiku" }
    ],
    "final_reviewers": []
  },
  "limits": { "inner_iterations": 2, "final_review_rounds": 0 },
  "plan_mode_gate": true
}
```

### `max-rigor` — all three lenses per iteration, on opus
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers": [
      { "use": "staff-review",  "model": "opus" },
      { "use": "thermonuclear", "model": "opus" },
      { "use": "code-review",   "model": "opus" }
    ],
    "final_reviewers": [
      { "use": "code-review", "model": "opus" }
    ]
  },
  "limits": { "inner_iterations": 5, "final_review_rounds": 3 },
  "plan_mode_gate": true
}
```

### `builtin-only` — no vendored engines (dependency-free smoke test)
```json
{
  "slots": {
    "validate":    { "use": "builtin" },
    "architect":   { "use": "builtin" },
    "implementer": { "use": "builtin" },
    "reviewers": [
      { "use": "builtin" }
    ],
    "final_reviewers": []
  },
  "limits": { "inner_iterations": 2, "final_review_rounds": 0 },
  "plan_mode_gate": false
}
```

## Overrides & validation

- `.devforge/config.json` is the committed default (devforge writes it on first run if
  missing).
- `.devforge/config.local.json` (gitignored) **shallow-merges** over it for
  per-environment tweaks — e.g. pointing a slot at a locally-installed skill instead of
  the vendored copy. This is the **only** place an installed plugin may be referenced.
- On every run the orchestrator validates the resolved config against
  `.devforge/registry.json`: every slot present; each `use` allowed in its slot; no
  duplicate `use` within a list. An invalid config **stops the run** with the exact
  error and the allowed list. `scripts/validate_config.py` encodes the same rules for
  CI.

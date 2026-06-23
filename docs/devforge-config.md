# devforge config

devforge configuration chooses the engine behind each stage, the model used for that
stage, the deterministic oracle commands, and the iteration limits for review loops.

The active config is `.devforge/config.json`. If it is missing, devforge copies the
default from `.claude/skills/devforge/config.default.json`. A local
`.devforge/config.local.json` may override values for one environment.

## Runtime files

Two files are intended for humans; the underscore-prefixed files are internal
context-routing state.

- `.devforge/1-triage.md`: cheap product decision, complexity, and approach sketch.
- `.devforge/2-design.md`: short human-reviewed plan or review scope.
- `.devforge/_user_request.md`: raw task, written before triage.
- `.devforge/_verified_task.md`: verified task with corrected current references.
- `.devforge/_request_fact_check.md`: evidence ledger for request claims.
- `.devforge/_panel.json`: approved per-run reviewer subset and limits.
- `.devforge/_state.json`: resume state, including `state.panel` after design approval.
- `.devforge/_progress.md`: resolved config, run notes, oracle status, and final links.

The configured reviewer lists are a roster. The design gate selects the run-specific
panel from that roster and writes it to `_panel.json`.

### Why one file per stage

Each stage writes one file and each role reads only what it needs, so context stays
scoped and reviewers stay independent. The implementer reads the distilled
`_verified_task.md`, not the raw `_request_fact_check.md`; reviewers judge the diff
against `2-design.md` and never see `claim.md` or each other's reviews. That blindness
is what keeps a multi-reviewer panel's signal independent.

Collapsing the files would either pollute role context or break reviewer independence.

## Stages

| Stage | Default `use` | Reads | Writes |
|---|---|---|---|
| `verify_request` | `brainstorming` | `_user_request.md`, `1-triage.md`, issue/code context | `_verified_task.md`, `_request_fact_check.md` |
| `architect` | `writing-plans` | `_verified_task.md`, `_request_fact_check.md`, `1-triage.md`, codebase | `2-design.md` |
| `implementer` | `feature-dev` | `_verified_task.md`, `_request_fact_check.md`, `2-design.md`, prior reviews | source edits, `claim.md` |
| `reviewers` | `staff-review` | `_verified_task.md`, `2-design.md`, diff, test output | `review-<use>.md` |
| `final_reviewers` | `thermonuclear`, `code-review` | `_verified_task.md`, `2-design.md`, diff, working tree | `final-review-<use>.md` |

`reviewers` run inside the implementation loop. `final_reviewers` run after the regular
loop is clean and can reopen a targeted fix round.

## Complexity defaults

The architect proposes the panel at the design gate. These defaults keep small changes
fast while still increasing scrutiny for broad or risky work.

| Tier | Use When | Default Panel |
|---|---|---|
| `trivial` | <=10 lines, 1 file, no logic change | 1 reviewer, no final, inner=1, rounds=0 |
| `small` | localized 1-3 file change | 1 reviewer, 1 final, inner=2, rounds=1 |
| `medium` | feature, shared helper, or multi-area fix | 1 reviewer, 2 final, inner=3, rounds=2 |
| `large` | core, many files, public API/response contract | full roster, inner=3, rounds=2 |

Core/shared or public-contract changes are `medium` at minimum regardless of line count.

## Default config

```json
{
  "stages": {
    "verify_request": { "use": "brainstorming", "model": "opus" },
    "architect": { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev", "model": "opus" },
    "reviewers": [{ "use": "staff-review", "model": "sonnet" }],
    "final_reviewers": [
      { "use": "thermonuclear", "model": "sonnet" },
      { "use": "code-review", "model": "sonnet" }
    ]
  },
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

`oracle.commands` should be finite and non-mutating. Good defaults for JS/TS repos are:

```json
{
  "oracle": {
    "commands": ["pnpm run check", "pnpm run test:unit"]
  }
}
```

Add targeted checks only for touched surfaces: builds, widget checks, agent/skill checks,
or specific integration tests. Avoid `dev`, `start`, watchers, fixers, cleanup commands,
inspectors, and eval workflows.

## Registry overrides

The shipped registry is `.claude/skills/devforge/registry.base.json`. A repo may add
`.devforge/registry.json` with extra `uses`; repo `uses` shallow-override base uses.
Base engine paths resolve relative to the skill. Repo engine paths resolve relative to
the repo.

Example:

```json
{
  "uses": {
    "dig": {
      "roles": ["architect"],
      "engine": ".claude/skills/dig/SKILL.md",
      "scope": "follow as instructions; write 2-design.md only"
    },
    "live-contract": {
      "roles": ["reviewer", "final_reviewer"],
      "engine": ".claude/agents/live-contract.md",
      "scope": "probe the live server; emit VERDICT then findings"
    }
  }
}
```

Then reference those `use` names in `.devforge/config.json`.

## Validation

On each run devforge validates:

- every stage is present
- every `use` exists
- the `use` supports the stage role
- reviewer and final reviewer lists contain no duplicate `use`

`scripts/validate_config.py` checks the same rules for CI and local tests.

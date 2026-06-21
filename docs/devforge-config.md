# devforge configuration

Slots are file contracts. Config chooses which vendored engine fills each slot and which
model it runs on. The oracle is separate: `oracle.commands` defines deterministic checks.

The base registry (`registry.base.json`) ships with the skill. Repos can add
`.devforge/registry.json` for domain engines. No wrapper skill is needed per engine.

## Flow & gates

The loop has **three human gates**: a cheap **triage gate** (go/no-go + complexity, before
any deep analysis), the **design gate** (approve the high-level plan *and* the verification
panel), and the **pre-merge gate**. Triage runs first and is deliberately high-level — it
exists so a not-worth-it, already-fixed, or duplicate task can be declined before paying for
the deep validate + architect work.

The configured `reviewers` / `final_reviewers` lists are a **roster**, not a fixed panel.
At the design gate the orchestrator proposes the **panel** — the subset to actually run for
*this* change (you can drop reviewers, drop a heavy/live-e2e final reviewer, and lower the
iteration budget for a small change, or keep everything for a risky one). The approved panel
must be a subset of the roster; it is recorded in `state.json` and drives the run.

### Complexity rubric → default panel

Triage rates the change with a consistent rubric; the tier sets the panel the design gate
starts from (then fine-tunes). Pick the tier whose **size or blast radius** fits — whichever
is higher.

| Tier | Size (rough) | Blast radius | Default panel |
|------|--------------|--------------|---------------|
| `trivial` | ≤10 lines, 1 file, no logic change | peripheral | 1 reviewer; no final; inner=1, rounds=0 |
| `small` | ~10–50 lines, 1–3 files, localized fix | no core/shared/contract code | 1 reviewer; 1 final; inner=2, rounds=1; no live-e2e |
| `medium` | ~50–300 lines, several files | shared helpers, not core architecture | 1 reviewer; 2 final; inner=3, rounds=2 |
| `large` | 300+ lines OR many files | core code, public API / response contract, widely-shared abstractions | full roster incl. live-e2e/contract reviewer; inner=3, rounds=2 |

**Blast-radius override:** a change touching core/shared code or a public API / response
contract is **`medium` at minimum**, regardless of line count. Defaults are bounded by the
configured roster — devforge never runs a `use` that isn't in config.

## The slots

| Slot | Runs | Reads | Writes | `use` options (default **bold**) | Model |
|------|------|-------|--------|----------------------------------|-------|
| `validate` | once, first | the task / issue, codebase | `task.md`, `validation.md` | **`brainstorming`** | opus |
| `architect` | once, after explore | `task.md`, `validation.md`, codebase | `design.md` (**high-level, ~1 page**) | **`writing-plans`** | opus |
| `implementer` | every iteration | `design.md`, prior reviews | source edits, `claim.md` | **`feature-dev`** | opus |
| `reviewers` (roster) | every iteration, parallel — panel subset only | `diff.patch`, `test-results.txt`, spec | `review-<use>.md` each | **`staff-review`**, `thermonuclear`, `code-review` | sonnet |
| `final_reviewers` (roster) | after convergence, parallel — panel subset only | `diff.patch` + working tree, spec | `final-review-<use>.md` each | **`thermonuclear`** + **`code-review`**, `staff-review` | sonnet |

`design.md` is a high-level plan a human reviews in one pass — approach, alternatives with
pros/cons, files (one line each), brief test strategy, risks. No code blocks or exhaustive
`file:line`; the implementer pins down exact signatures and call sites.

Default engine focus:

| `use` | Focus |
|---|---|
| `brainstorming` | validate task and issue claims |
| `writing-plans` | write `design.md` |
| `feature-dev` | implement the approved design |
| `staff-review` | correctness, edge cases, tests |
| `thermonuclear` | maintainability and structure |
| `code-review` | bug/quality pass with confidence scoring |

## Oracle, Limits & Gate

```json
{
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

- `oracle.commands` — ordered, finite, non-mutating checks. Empty means devforge infers
  and records the smallest credible check; if it cannot, the oracle is not green.
- `inner_iterations` — implement→oracle→reviewers rounds before escalating. This is the
  roster default; the design-gate panel may lower it for a small change.
- `final_review_rounds` — how many times a final review may reopen the inner loop. A
  reopen re-runs **only the final reviewers** (the per-iteration reviewers already passed
  the converged diff). Panel may lower this too.
- `plan_mode_gate` — when true and running interactively in the CLI, the **triage gate** and
  **design gate** render their artifact (`triage.md` / `design.md` + the proposed panel) in
  Claude Code's plan-mode for native approve/reject (the orchestrator calls `EnterPlanMode`,
  mirrors the artifact into the plan file, then `ExitPlanMode`); otherwise (and always on
  web/headless) they fall back to `/devforge-approve-triage` / `/devforge-approve-design`.
  The marker files are the source of truth either way.

## Default Config

### `default`
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers": [
      { "use": "staff-review",  "model": "sonnet" }
    ],
    "final_reviewers": [
      { "use": "thermonuclear", "model": "sonnet" },
      { "use": "code-review",   "model": "sonnet" }
    ]
  },
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

Per-iteration review stays lean (`staff-review`). Heavier lenses run as final reviewers.

### Choosing oracle commands from `package.json`

For package scripts like `check`, `test:unit`, `build`, `check:widgets`, `check:agents`,
`test:integration:*`, `dev`, `start`, `lint:fix`, and `format`, a good default is:

```json
{
  "oracle": {
    "commands": ["pnpm run check", "pnpm run test:unit"]
  }
}
```

Add targeted checks when the task touches those surfaces:

```json
{
  "oracle": {
    "commands": [
      "pnpm run check",
      "pnpm run test:unit",
      "pnpm run build",
      "pnpm run check:widgets"
    ]
  }
}
```

- `pnpm run build`: TypeScript references, generated `dist`, web assets, runtime entrypoints.
- `pnpm run check:widgets`: widget contracts or web widget files.
- `pnpm run check:agents`: agent/skill links or docs.
- `pnpm run test:integration:stdio`: only when that integration path changed.
- Avoid routine use of `start`, `dev`, `build:watch`, `lint:fix`, `format`, `clean`,
  inspectors, and eval workflows.

## Base + repo registries

The base registry travels with the skill. A repo can add `.devforge/registry.json` with
extra `uses`; repo uses shallow-override base uses by name. `slot_roles` always comes from
the base. Base engine paths resolve relative to the skill; repo engine paths resolve
relative to the repo root. devforge logs the fully resolved registry to `progress.md`.

### Recipe: add a domain engine in a target repo

Example repo registry:

```jsonc
// <target-repo>/.devforge/registry.json   — committed in that repo, deltas only
{
  "$comment": "Domain engines only. Generic engines come from devforge's base registry.",
  "uses": {
    "dig": {
      "roles": ["architect"],
      "engine": ".claude/skills/dig/SKILL.md",
      "scope": "follow as instruction text; plan using its resources + conventions; STRIP its own gate and issue-creation; write design.md only"
    },
    "mcpc-tester": {
      "roles": ["reviewer", "final_reviewer"],
      "engine": ".claude/agents/mcpc-tester.md",
      "scope": "follow as instruction text; build + probe the live server; emit VERDICT then findings"
    }
  }
}
```

Then wire those `use` names in `.devforge/config.json`:

```jsonc
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "dig",           "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers":       [ { "use": "staff-review",  "model": "sonnet" } ],
    "final_reviewers": [ { "use": "thermonuclear", "model": "sonnet" },
                         { "use": "code-review",   "model": "sonnet" },
                         { "use": "mcpc-tester",   "model": "sonnet" } ]
  },
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

No devforge code change is needed.

## Overrides & validation

- `.devforge/config.json` is an optional project override. If it is missing, devforge
  writes the default from `config.default.json` shipped beside the skill. The schema stays
  with the skill at `devforge/config.schema.json`; repo configs are validated against that
  shipped schema instead of carrying a duplicate schema file.
- `.devforge/config.local.json` (gitignored) **shallow-merges** over it for
  per-environment tweaks — e.g. pointing a slot at a locally-installed skill instead of
  the vendored copy. This is the **only** place an installed plugin may be referenced.
- On every run the orchestrator validates the resolved config against the **resolved
  registry** (base + any repo `.devforge/registry.json`): every slot present; each `use`
  allowed in its slot; no duplicate `use` within a list. An invalid config **stops the run**
  with the exact error and the allowed list. `scripts/validate_config.py` encodes the same
  rules for CI.

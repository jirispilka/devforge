# devforge

A controlled, **gated agentic coding loop** for Claude Code. Point it at a task and it
walks the task through human-gated phases, keeping the implementer and reviewer
independent so the reviewer judges the *actual change* — never the implementer's pitch.

```
/devforge <task>
   triage (product decision + complexity) → [TRIAGE GATE: human] →
   validate → explore → architect → [DESIGN GATE: human approves plan + review panel] →
     ┌─ iteration N ──────────────────────────────────────────────┐
     │ implementer edits source, writes claim.md                   │
     │ orchestrator runs the oracle commands + computes diff       │
     │ reviewers (parallel, e.g. correctness + maintainability)    │
     │   each read the diff → review-<use>.md (PASS/FAIL)          │
     │ green + all findings resolved → converged │ else → next iter│
     └─────────────────────────────────────────────────────────────┘
   final reviewers (2nd-angle pass) → findings reopen the loop, else
   → [PRE-MERGE GATE: human] → merge
```

Triage runs first and is cheap: a high-level product call (proceed / defer / decline) plus a
complexity estimate — so a not-worth-it or already-fixed task is declined before any deep
analysis. The design is kept to ~1 page (approach + pros/cons + files), and at the design
gate the orchestrator proposes the **verification panel** — which reviewers actually run for
*this* change — so a minor bug isn't reviewed like a risky refactor.

Runs locally **and** on claude.ai/code (web). Setup is just "attach the repo" — it's
pure skills: no plugin, no install, no settings prompt.

## Core Rules

- Human gates control the consequential decisions: triage go/no-go, design + panel
  approval, and merge/PR.
- The oracle is deterministic checks from `oracle.commands`; it is not a model opinion.
- Reviewers are blind to `claim.md` and peer reviews. They judge `task.md`, `design.md`,
  `diff.patch`, and `test-results.txt`.
- Every reviewer finding, including nits, is fixed or explicitly skipped before merge.
- Issue-like tasks get a staleness check before design, so stale code refs do not become
  new work.

Run data lives in `.devforge/`; the tool lives in `.claude/skills/`. Durable run records
are committed, while regenerable `diff.patch` and `test-results.txt` are gitignored.

## Use

- **As a plugin (recommended):** add this repo as a marketplace and install — the plugin
  bundles the skills, the vendored engines, and the base registry:
  ```
  /plugin marketplace add jirispilka/devforge
  /plugin install devforge@devforge
  ```
  For local development, skip the marketplace and load the dir directly:
  `claude --plugin-dir /path/to/devforge/.claude`.
- **On web:** attach this repo to a claude.ai/code session — the skills load automatically.
- **In another repo:** copy `.claude/skills/` into it (it travels; domain context stays put).
- **Commands:** `/devforge <task>` to run; `/devforge-approve-triage`,
  `/devforge-approve-design`, and `/devforge-approve-merge` are the human-only approvals —
  each records its gate and **auto-continues** the loop. (`/devforge` with no args resumes an
  interrupted run.) Type the commands bare (no `devforge:` prefix) whether installed as a
  plugin or attached standalone / on web: `/devforge`, `/devforge-approve-triage`,
  `/devforge-approve-design`, `/devforge-approve-merge`.

## Configuration

Each phase is a slot filled by an engine named in `.devforge/config.json`. The base
registry ships with the skill; repos can add `.devforge/registry.json` for domain engines.
Default config:

```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers":       [ { "use": "staff-review", "model": "sonnet" } ],
    "final_reviewers": [ { "use": "thermonuclear", "model": "sonnet" },
                         { "use": "code-review", "model": "sonnet" } ]
  },
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

Use finite, non-mutating oracle commands: type checks, lint checks, builds, unit tests, and
targeted integration tests. Avoid dev servers, watch commands, fixers, cleanup commands,
inspectors, and eval workflows for routine oracle runs.

Full config catalog and examples: [`docs/devforge-config.md`](docs/devforge-config.md).
Vendored engine provenance: [`VENDORED.md`](VENDORED.md).

## Layout

```
.claude/                 the plugin root (source: "./.claude" in marketplace.json)
  .claude-plugin/plugin.json  plugin manifest (name: devforge)
.claude/skills/          the tool (loads on web; never holds run data)
  devforge/SKILL.md                the orchestrator (incl. the universal slot-dispatch contract)
  devforge/config.default.json      default config copied to .devforge/config.json on first run
  devforge/config.schema.json       schema used to validate generated/project config
  devforge/registry.base.json      the base registry — generic engines (merged with a repo's deltas)
  devforge-approve-triage/             human-only triage-gate approval
  devforge-approve-design/             human-only design-gate approval
  devforge-approve-merge/              human-only pre-merge-gate approval
  _vendored/                  faithful upstream engine copies (see VENDORED.md)
.claude/agents/          devforge-code-explorer / -architect (grounding agents)
.claude-plugin/marketplace.json  marketplace catalog (points at ./.claude)
.devforge/               a run's working files (+ optional repo config.json / registry.json)
docs/devforge-config.md  the configuration catalog
scripts/validate_config.py  config validator (CI/tests; rules mirror the orchestrator)
tests/                   structural test suite (schema, registry, vendoring, no-install)
VENDORED.md              vendored-engine provenance
.gitignore               ignores .devforge transients + config.local.json
```

# devforge

A human-gated coding loop for Claude Code. `/devforge <task>` keeps product decisions,
implementation, review, tests, and merge approval separated through files in `.devforge/`.
Reviewers judge the diff and test output, not the implementer's claim.

## Flow

```text
/devforge <task>
  triage product decision -> approve triage
  validate + explore + design -> approve design + review panel
  implement -> oracle checks -> blind reviewers -> final reviewers
  approve merge -> commit / PR
```

Triage is deliberately cheap: persist the raw request, decide `PROCEED | DEFER | DECLINE`,
estimate complexity, and avoid deep implementation detail. The design stays about one page.
At the design gate, devforge writes `panel.json` so a small bug can use a small review
panel and a risky change can use the full roster.

## Commands

- `/devforge <task>` starts a run.
- `/devforge` resumes a run from `.devforge/state.json`.
- `/devforge-approve-triage`, `/devforge-approve-design`, and
  `/devforge-approve-merge` are human-only gates; each records its marker and auto-continues.

## Install / Use

```text
/plugin marketplace add jirispilka/devforge
/plugin install devforge@devforge
```

For local development, load the plugin dir directly:

```bash
claude --plugin-dir /path/to/devforge/.claude
```

On claude.ai/code, attach this repo. In another repo, copy `.claude/skills/` or install as
a plugin. Use the commands without a `devforge:` prefix.

## Files

- Tooling lives in `.claude/skills/`.
- Run data lives in `.devforge/`.
- Durable evidence files are committed: request, triage, task, validation, design, panel,
  reviews, claims, approvals, and progress.
- Regenerable files are ignored: `iter-*/diff.patch` and `iter-*/test-results.txt`.

## Configuration

Stages are configured in `.devforge/config.json`; defaults ship beside the skill in
`.claude/skills/devforge/config.default.json`. The base registry maps each `use` name to a
vendored engine under `.claude/skills/_vendored/`.

Default roster:

```json
{
  "stages": {
    "validate": { "use": "brainstorming", "model": "opus" },
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

Use finite, non-mutating oracle commands such as type checks, lint checks, builds, unit
tests, and targeted integration tests. Avoid dev servers, watchers, fixers, cleanup
commands, inspectors, and eval workflows.

More detail:

- Config reference: [docs/devforge-config.md](docs/devforge-config.md)
- Vendored engine provenance: [VENDORED.md](VENDORED.md)

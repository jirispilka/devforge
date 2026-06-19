# devforge

A controlled, **gated agentic coding loop** for Claude Code. Point it at a task and it
walks the task through human-gated phases, keeping the implementer and reviewer
independent so the reviewer judges the *actual change* — never the implementer's pitch.

```
/devforge <task>
   validate → explore → architect → [DESIGN GATE: human] →
     ┌─ iteration N ──────────────────────────────────────────────┐
     │ implementer edits source, writes claim.md                   │
     │ orchestrator runs the oracle (tests/lint) + computes diff   │
     │ reviewer reads the diff + results → review.md (PASS/FAIL)   │
     │ green + all findings resolved → done │ else → next iter │ 3 fails → escalate │
     └─────────────────────────────────────────────────────────────┘
   → [PRE-MERGE GATE: human] → merge
```

Runs locally **and** on claude.ai/code (web). Setup is just "attach the repo" — it's
pure skills: no plugin, no install, no settings prompt.

## Why it's built this way

- **Gate only the consequential decisions** (the design, the merge) — human-in-the-loop
  without approval fatigue. Everything between the gates runs unattended.
- **Verify with a deterministic oracle + an independent critic**, never the model's own
  say-so. LLMs confidently approve their own wrong output.
- **Reward hacking is real** (delete the failing test to go green). So: the orchestrator
  runs the oracle (the implementer can't fake results), the implementer must **never edit
  or delete tests to pass**, and the reviewer is **blind to the implementer's claims**.
- **Issues drift.** A GitHub issue filed weeks ago cites files that moved, symbols that
  were renamed, or a bug that's already fixed. The **validate** phase verifies an issue's
  claims against the *current* code before any design is drawn.
- **Don't stop at "good enough."** Every reviewer finding — down to nits — is fixed or
  explicitly justified before the merge gate. Nothing reaches the gate "noted but
  unhandled."

## How it works

### Two self-enforced gates

`/devforge` checks for marker files and **refuses to proceed without them**:

- It won't edit source until `.devforge/design.approved` exists.
- It won't push / merge / open a PR until `.devforge/merge.approved` exists.

A human writes those markers with the human-only skills **`/devforge-approve-design`**
and **`/devforge-approve-merge`** (they carry `disable-model-invocation: true`, so the
agent can't self-approve). After approving, the loop **continues automatically** — the approval skill
hands straight back to `/devforge` (which also **resumes from `.devforge/state.json`** if
a run is ever interrupted, and never restarts one in progress). There are
no hooks — the gates are enforced by the orchestrator following the skill, and the
**human review is the real guarantee**. Simpler, and no "trust the hooks?" prompt for
teammates.

### Working files live in `.devforge/`

Everything a run produces goes in **`.devforge/`** at the repo root — never under
`.claude/`, which is reserved for the tool (the skills). The implementer and reviewer
hand off **only through these files**:

| File | Written by | Read by | Committed? |
|------|-----------|---------|-----------|
| `task.md` | validate | all | yes |
| `validation.md` | validate | human, all | yes |
| `design.md` | architect | impl, reviewer | yes |
| `design.approved` | **human** `/devforge-approve-design` | gate check | yes |
| `state.json`, `progress.md` | orchestrator | resume / human | yes |
| `iter-N/claim.md` | implementer | **human only** | yes |
| `iter-N/diff.patch` | orchestrator (`git diff`) | reviewer | no (gitignored) |
| `iter-N/test-results.txt` | orchestrator (oracle) | reviewer | no (gitignored) |
| `iter-N/review.md` | reviewer | impl (next iter) | yes |
| `merge.approved` | **human** `/devforge-approve-merge` | gate check | yes |

Durable records are committed on the feature branch (the PR carries the paper trail and
web sessions can resume); regenerable transients (`diff.patch`, `test-results.txt`) are
gitignored.

**Independence rule:** the reviewer reads `task.md`, `design.md`, `diff.patch`,
`test-results.txt` — **never `claim.md`.** It judges reality against the approved spec,
blind to the implementer's narrative. Independence = separate context + a different model
+ blindness to the claim.

### Roles are file contracts; slots are config

A *role* (implementer, reviewer, …) is defined only by the files it reads and writes.
What *fills* it — a skill or agent, on a chosen model — is a config value, so you can swap
a role without touching the loop. The implementer and reviewer are swappable slots; the
**oracle (tests/lint) is not** — it's the deterministic ground truth.

### Validate catches stale issues

When the task is a GitHub issue (or cites code locations), validate builds a claim ledger
from the issue, then checks each claim against the current `HEAD` (`gh` + `git log
--since=<createdAt>` / `-S<symbol>` / `--grep="#<n>"` + grep). It writes
`.devforge/validation.md` marking each claim `VALID | STALE | LIKELY-FIXED |
UNVERIFIABLE`, and **stops to ask the human** if core claims are stale or the issue looks
already-fixed — so the design is built on current reality.

## Use

- **On web:** attach this repo to a claude.ai/code session — the skills load automatically.
- **In another repo:** copy `.claude/skills/` into it (it travels; domain context stays put).
- **Commands:** `/devforge <task>` to run; `/devforge-approve-design` and
  `/devforge-approve-merge` are the human-only approvals — each records its gate and
  **auto-continues** the loop. (`/devforge` with no args resumes an interrupted run.)

## Status

- **Built — control plane:** the `/devforge` orchestrator (skeleton), the two human-only
  approvals, self-enforced gates, the `.devforge/` file contract, and the validate-phase
  claim/staleness check.
- **Planned — enrichment:** a `.devforge/config.json` for the swappable slots; full
  subagent dispatch (implementer on `opus`, reviewer on `sonnet`); and the reused skills
  below, **vendored** into `.claude/skills/` (plugins can't be installed on web), each
  recorded in a `VENDORED.md` with its upstream source + commit for deliberate re-sync:
  - **`staff-review`** — from `apify/agent-skills-internal` (the default reviewer).
  - a **Superpowers subset** — from `obra/superpowers`: `brainstorming` (validate),
    `writing-plans` (architect), `systematic-debugging` (debug),
    `verification-before-completion` (completion guard),
    `finishing-a-development-branch` (merge), `test-driven-development`.

  Domain skills (e.g. an MCP repo's `dig` / `mcpc-tester`) are **not** vendored — they
  stay in their target repo and are optional slot swaps where installed.

## Layout

```
.claude/skills/          the tool (loads on web; never holds run data)
  devforge/SKILL.md           the orchestrator
  devforge-approve-design/    human-only design-gate approval
  devforge-approve-merge/     human-only pre-merge-gate approval
.devforge/               a run's working files (created at runtime; mostly committed)
.gitignore               ignores .devforge transients + config.local.json
```

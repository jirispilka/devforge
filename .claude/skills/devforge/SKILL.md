---
name: devforge
description: Run a task through the gated coding loop — validate, explore, architect, STOP for human design approval, then implement ↔ review ↔ test, STOP for human pre-merge approval, then merge. Use this to drive any non-trivial change through controlled, human-gated steps where the implementer and reviewer stay independent and coordinate only through files. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge — gated loop orchestrator

You are the **orchestrator** (the only conductor). You drive the phases and mediate
all hand-offs **through files under `.devforge/`** — the implementer and reviewer
never see each other's context. Two human gates stand between phases: you cannot edit
source before the design is approved, and cannot push/merge before merge is approved.

> **Working files live in `.devforge/` at the repo root — never under `.claude/`.**
> `.claude/skills/` is the tool (config); `.devforge/` is this run's data.

> **Config-driven slots.** Each phase is a *slot* filled by a vendored skill named in
> `.devforge/config.json` and run through a thin adapter under `.claude/skills/`. The
> default slots: validate ← `brainstorming`, architect ← `writing-plans`, implementer ←
> `feature-dev`, reviewers ← `staff-review` + `thermonuclear` (parallel, every
> iteration), final_reviewers ← `code-review` (after convergence). Every engine is
> **vendored in-repo** (`.claude/skills/_vendored/`) — nothing needs installing. See
> `docs/devforge-config.md` for the catalog. The oracle (tests/lint) is **not** a slot.

## File contract (`.devforge/`)

| File | Writer | Reader | Committed? |
|------|--------|--------|-----------|
| `config.json` | orchestrator (default) / human | orchestrator | yes |
| `config.local.json` | human (optional) | orchestrator | no (gitignored) |
| `registry.json` | tool | orchestrator | yes |
| `task.md` | validate slot | all | yes |
| `validation.md` | validate slot | human, all | yes |
| `design.md` | architect slot | impl, reviewers | yes |
| `design.approved` | **human** `/devforge-approve-design` | gate check | yes |
| `state.json` | orchestrator | resume | yes |
| `progress.md` | orchestrator | human | yes |
| `iter-N/claim.md` | implementer | **human only** | yes |
| `iter-N/diff.patch` | orchestrator (`git diff`) | reviewers | no (gitignored) |
| `iter-N/test-results.txt` | orchestrator (oracle) | reviewers | no (gitignored) |
| `iter-N/review-<use>.md` | each per-iteration reviewer | impl (next iter), orchestrator | yes |
| `iter-N/final-review-<use>.md` | each final reviewer | impl (next iter), orchestrator | yes |
| `merge.approved` | **human** `/devforge-approve-merge` | gate check | yes |

`<use>` is the slot value's `use` name (e.g. `review-staff-review.md`,
`review-thermonuclear.md`, `final-review-code-review.md`).

**Independence rule:** every reviewer reads `task.md`, `design.md`, `iter-N/diff.patch`,
`iter-N/test-results.txt` — **never `claim.md`, and never another reviewer's output.**
Each judges reality against the approved spec, blind to the implementer's narrative and
to its peers.

## Procedure

### 0. Setup or resume
- `mkdir -p .devforge`.
- **Resume check (do this first):** if `.devforge/state.json` already exists, READ it
  and **continue from where it left off — do not restart:**
  - If invoked with a `<task>` that differs from `.devforge/task.md`, ask the human
    whether to continue the existing run or start fresh (starting fresh clears `.devforge/`).
  - `phase=design-gate` and `.devforge/design.approved` now exists → go to the inner
    loop (step 5).
  - `phase` is in the inner loop → continue at the current `iteration`.
  - `phase=pre-merge-gate` and `.devforge/merge.approved` exists → go to finish (step 7).
  - Otherwise, re-announce the gate you're waiting on.
- **Fresh start** (no `state.json`): write `.devforge/task.md` = the `<task>` argument;
  initialize `.devforge/state.json` =
  `{"phase":"validate","iteration":0,"head_sha":"<git rev-parse HEAD>"}`; start
  `.devforge/progress.md` with a header and a timestamped "loop started" line.
- **Load + validate config (every start, fresh or resume):**
  - If `.devforge/config.json` is absent, write the committed default (the schema in
    `config.schema.json`); tell the human it was created and is editable.
  - If `.devforge/config.local.json` exists, **shallow-merge** it over `config.json`
    (per-slot overrides win) — use it, don't rewrite `config.json`.
  - **Validate** the resolved config against `.devforge/registry.json` (the rules
    `scripts/validate_config.py` encodes): every slot present; each slot's `use` is in
    that slot's allowed list; no duplicate `use` within `reviewers` / `final_reviewers`.
    On any error, **STOP** and print the exact problem and the slot's allowed list — do
    not run with an invalid config.
  - Read `limits.inner_iterations` (default 3), `limits.final_review_rounds` (default
    2), and `plan_mode_gate` (default true). Record the resolved config in
    `progress.md`.

> **Slot dispatch (how a slot runs).** To run a slot, resolve its `use` to an adapter
> skill via this map, then dispatch a subagent **on the slot's `model`** and tell it to
> follow that adapter's `SKILL.md`:
>
> | `use` | adapter skill |
> |-------|---------------|
> | `brainstorming` | `devforge-validate-brainstorm` |
> | `writing-plans` | `devforge-architect-plans` |
> | `feature-dev` | `devforge-impl-feature-dev` |
> | `staff-review` | `devforge-review-staff` |
> | `thermonuclear` | `devforge-review-thermo` |
> | `code-review` | `devforge-review-code` |
> | `builtin` | the inline skeleton step described in that phase below |
>
> The subagent communicates only through `.devforge/` files. Reviewers are dispatched
> **blind to `claim.md`** and to each other.

> **Approval auto-continues.** At each gate the human runs the human-only approval skill,
> which records the marker and then **hands straight back to `/devforge`** — the loop
> continues without the human re-invoking anything. Re-running `/devforge` also resumes
> from `state.json` (the fallback if a run is ever interrupted); it never restarts a run
> already in progress.

### 1. Validate — incl. claim & staleness check
**Run the `validate` slot** (dispatch per *Slot dispatch* — default `brainstorming` via
`devforge-validate-brainstorm`). Confirm the task is specific enough to act on **and that
its premises are still true.** The steps below are the contract the slot fulfils.

**If the task references a GitHub issue (number/URL) or cites specific code locations,**
run a staleness check *before designing* — issues drift from the code (files move,
symbols get renamed, the bug may already be fixed):
1. **Fetch + timestamp:** `gh issue view <n> --json title,body,createdAt,comments,labels`.
   Record `createdAt` as the staleness baseline.
2. **Claim ledger:** from the body + comments, list code refs (paths, `symbols`,
   `file:line`, permalinks that pin a SHA), behavioral claims, causal claims
   ("introduced by #N"), and repro steps.
3. **Verify each against current HEAD:**
   - References: does the file/symbol still exist? `grep`/Read it; if a permalink
     pinned a SHA, check whether the file moved/changed since. Mark
     resolved / moved→<new> / gone.
   - Drift since filing: `git log --since="<createdAt>" --oneline -- <paths>` and
     `git log -S"<symbol>"` to see if the area changed after the issue was filed.
   - Already-fixed: `git log --grep="#<n>"` and merged PRs referencing the issue.
4. **Write `.devforge/validation.md`:** each claim → `VALID | STALE(→corrected ref) |
   LIKELY-FIXED | UNVERIFIABLE` with evidence (HEAD `file:line`, commit SHAs), plus a
   one-line verdict.
5. **Calibrated stop:** if core claims are STALE or it looks LIKELY-FIXED, STOP and
   surface to the human with a recommendation (re-scope / close as fixed / proceed with
   corrected references) before designing. Otherwise write `task.md` using the
   **corrected, current** references — never the stale ones.

Then restate the task, list any genuine ambiguities, and set `state.phase="explore"`.

### 2. Explore  *(orchestrator-owned — not a slot)*
Read the relevant parts of the codebase to ground the design. Note key files/patterns
in `progress.md`. Set `state.phase="architect"`.

### 3. Architect
**Run the `architect` slot** (default `writing-plans` via `devforge-architect-plans`).
It writes `.devforge/design.md`: the approach, the specific files to change, the test
strategy (the oracle), and risks. This is the artifact reviewed at the design gate.
Set `state.phase="design-gate"`.

### 4. DESIGN GATE  — STOP
- **Self-enforce:** do **not** edit any source file until `.devforge/design.approved`
  exists. This gate is enforced by you following this skill — there are no hooks.
- **Plan-mode front-end (when `plan_mode_gate` is true AND running interactively in the
  CLI):** present `design.md` to the human via `ExitPlanMode` (the design *is* the
  plan). On approval, write `.devforge/design.approved` yourself and continue the loop.
  This gives the native approve/reject UX while keeping the marker file as the source of
  truth.
- **Otherwise** (`plan_mode_gate` false, or running on web/headless, or resuming): tell
  the human to review `.devforge/design.md`, then run **`/devforge-approve-design`** — it
  records the marker and continues automatically. Then stop and wait.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/design.approved` exists.

### 5. Inner loop  (implement → oracle → reviewers), iteration N = 1, 2, …
For each iteration, make a fresh `.devforge/iter-N/` directory, then:
- **Implement** — run the `implementer` slot (default `feature-dev` via
  `devforge-impl-feature-dev`) on `slots.implementer.model`. It applies `design.md` and
  **addresses every finding from all of the prior iteration's `review-*.md` /
  `final-review-*.md` — blockers AND nits** (smallest proportionate fix; skip only with a
  specific recorded reason — "out of scope" alone is not a reason). It must **never edit
  or delete tests to pass**, and writes `iter-N/claim.md`.
- **Oracle** (orchestrator, not a slot): run the project's tests/lint; redirect output
  to `iter-N/test-results.txt`. Produce the ground-truth diff:
  `git add -A && git diff --cached -U10 > iter-N/diff.patch` (then unstage if needed).
- **Reviewers (parallel)** — dispatch **one subagent per entry in `reviewers`**,
  concurrently, each on its `model`, each following its adapter, each **blind to
  `claim.md` and to the other reviewers**. Each writes `iter-N/review-<use>.md` (first
  line `VERDICT: PASS|FAIL`, severity-tagged findings). Default: `staff-review`
  (correctness) **and** `thermonuclear` (maintainability).
- **Decide**: converged only when the oracle is green **and every finding across ALL
  `iter-N/review-*.md` is resolved** — fixed or carrying an explicit skip-justification,
  **nits included**. A `PASS` that still lists actionable findings is **not** done. Where
  two reviewers conflict (e.g. a structural restructure vs a minimal-diff preference),
  pick the resolution and record the reconciliation for the next `claim.md`. If the
  oracle is red or findings remain, feed the reviews into iteration N+1. After
  `inner_iterations` (default 3) without converging — or a genuine blocker the design
  can't resolve — STOP and escalate. Append a line to `progress.md` each iteration.

### 5b. Final review  (after the inner loop converges)
If `final_reviewers` is non-empty, dispatch **one subagent per entry**, in parallel,
each on its `model`, each following its adapter, blind to `claim.md` and to each other,
each writing `iter-N/final-review-<use>.md`. Default: `code-review`.
- **If any final review has actionable findings**, they reopen the inner loop: run a
  fresh implement → oracle → reviewers iteration to resolve them, then re-run the final
  reviewers. This reopen-cycle is bounded by `final_review_rounds` (default 2); exceeding
  it STOPs and escalates.
- **When all final reviews are clean** (or `final_reviewers` is empty), proceed to the
  pre-merge gate.

### 6. PRE-MERGE GATE — STOP
- **Self-enforce:** do not push / merge / open a PR until `.devforge/merge.approved`
  exists. Summarize the evidence for the human — the change, the oracle status, and
  confirm **every finding from all reviewers (per-iteration AND final) is resolved**
  (fixed or justified-skip, nits included; no "noted but unhandled"). Present the diff
  clearly: a `git diff --stat` summary plus the actual hunks, so the human reviews the
  real change. Then tell them the exact next step: review `.devforge/`, then run
  **`/devforge-approve-merge`** — it records approval and continues to commit + PR
  automatically. Then stop and wait.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/merge.approved` exists.

### 7. Finish
Commit, then push / open a PR as appropriate. Record the outcome in `progress.md`.

## Rules
- Only write inside `.devforge/` until `design.approved` exists.
- Trust the oracle (tests/lint), not self-reports. Never weaken or delete tests.
- **Resolve every finding from every reviewer — per-iteration and final — before the
  pre-merge gate, including nits.** Each is fixed or skipped with a specific recorded
  reason; never carry an unhandled finding to the gate.
- Keep every reviewer blind to `claim.md` and to the other reviewers. Keep yourself the
  only component that sees every file.
- Use only the slots in the validated config. Never substitute an installed plugin for a
  vendored engine unless `config.local.json` explicitly says so.

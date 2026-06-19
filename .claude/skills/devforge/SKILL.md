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

> **Build status: SKELETON (Phase 1).** The flow and both gates are real; the
> per-phase work below is intentionally minimal. Phase 3 swaps the marked steps for
> vendored skills (brainstorming, writing-plans, staff-review, systematic-debugging,
> verification-before-completion, finishing-a-development-branch) driven by
> `.devforge/config.json`. Keep the file contract below stable.

## File contract (`.devforge/`)

| File | Writer | Reader | Committed? |
|------|--------|--------|-----------|
| `task.md` | orchestrator (validate) | all | yes |
| `validation.md` | orchestrator (validate) | human, all | yes |
| `design.md` | orchestrator (architect) | impl, reviewer | yes |
| `design.approved` | **human** `/devforge-approve-design` | gate check | yes |
| `state.json` | orchestrator | resume | yes |
| `progress.md` | orchestrator | human | yes |
| `iter-N/claim.md` | implementer | **human only** | yes |
| `iter-N/diff.patch` | orchestrator (`git diff`) | reviewer | no (gitignored) |
| `iter-N/test-results.txt` | orchestrator (oracle) | reviewer | no (gitignored) |
| `iter-N/review.md` | reviewer | impl (next iter), orchestrator | yes |
| `merge.approved` | **human** `/devforge-approve-merge` | gate check | yes |

**Independence rule:** the reviewer reads `task.md`, `design.md`, `iter-N/diff.patch`,
`iter-N/test-results.txt` — **never `claim.md`.** It judges reality against the
approved spec, blind to the implementer's narrative.

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

> **Approval auto-continues.** At each gate the human runs the human-only approval skill,
> which records the marker and then **hands straight back to `/devforge`** — the loop
> continues without the human re-invoking anything. Re-running `/devforge` also resumes
> from `state.json` (the fallback if a run is ever interrupted); it never restarts a run
> already in progress.

### 1. Validate — incl. claim & staleness check  *(Phase 3: brainstorming; richer issue analysis via a domain skill where installed)*
Confirm the task is specific enough to act on **and that its premises are still true.**

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

### 2. Explore  *(skeleton — Phase 3: Explore subagent / dig)*
Read the relevant parts of the codebase to ground the design. Note key files/patterns
in `progress.md`. Set `state.phase="architect"`.

### 3. Architect  *(skeleton — Phase 3: writing-plans)*
Write `.devforge/design.md`: the approach, the specific files to change, the test
strategy (the oracle), and risks. This is the artifact reviewed at the design gate.
Set `state.phase="design-gate"`.

### 4. DESIGN GATE  — STOP
- **Self-enforce:** do **not** edit any source file until `.devforge/design.approved`
  exists. This gate is enforced by you following this skill — there are no hooks.
- Tell the human: review `.devforge/design.md`, then run **`/devforge-approve-design`** —
  it records approval and continues the loop automatically (no need to re-run `/devforge`).
  Then stop and wait.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/design.approved` exists.

### 5. Inner loop  (implement ↔ oracle ↔ review), iteration N = 1, 2, …
For each iteration, make a fresh `.devforge/iter-N/` directory, then:
- **Implement** *(skeleton — Phase 3: dispatch implementer subagent on its configured
  model)*: apply `design.md`, and **address every finding from the prior
  `iter-(N-1)/review.md` — blockers AND nits.** Apply the smallest fix that resolves each
  finding that is a real, proportionate improvement (nits included). Skip a finding only
  if it is genuinely unnecessary or disproportionate to its severity, and record the
  **specific** reason in `claim.md` ("out of scope" alone is not a reason). Never edit or
  delete tests to pass. Write `iter-N/claim.md` = what you did, what you skipped + why,
  and evidence.
- **Oracle**: run the project's tests/lint; redirect output to
  `iter-N/test-results.txt`. Produce the ground-truth diff:
  `git add -A && git diff --cached -U10 > iter-N/diff.patch` (then unstage if needed).
- **Review** *(skeleton — Phase 3: dispatch reviewer on a different model; adapter
  invokes vendored staff-review)*: judge `diff.patch` + `test-results.txt` against
  `task.md`/`design.md` — **without reading `claim.md`**. Write `iter-N/review.md` with a
  first line `VERDICT: PASS|FAIL` and findings, each tagged by severity
  (blocker/major/minor/nit).
- **Decide**: the loop is done only when the oracle is green **and there are no
  unresolved findings** — every finding from the latest review is either fixed or carries
  an explicit skip-justification, **including nits**. A `VERDICT: PASS` that still lists
  actionable nits is **not** done: run another iteration to fix or justify them. If the
  oracle is red or blockers remain, feed `review.md` into iteration N+1. After **3**
  iterations without converging (or a genuine blocker the design can't resolve), STOP and
  escalate to the human. Append a line to `progress.md` each iteration.

### 6. PRE-MERGE GATE — STOP
- **Self-enforce:** do not push / merge / open a PR until `.devforge/merge.approved`
  exists. Summarize the evidence for the human — the change, the oracle status, and
  confirm **all reviewer findings are resolved** (fixed or justified-skip, nits included;
  there should be no "noted but unhandled" findings). Then tell them the exact next
  step: review `.devforge/`, then run **`/devforge-approve-merge`** — it records approval
  and continues to commit + PR automatically. Then stop and wait.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/merge.approved` exists.

### 7. Finish  *(skeleton — Phase 3: finishing-a-development-branch)*
Commit, then push / open a PR as appropriate. Record the outcome in `progress.md`.

## Rules
- Only write inside `.devforge/` until `design.approved` exists.
- Trust the oracle (tests/lint), not self-reports. Never weaken or delete tests.
- **Resolve every reviewer finding before the pre-merge gate — including nits.** Each is
  either fixed or skipped with a specific recorded reason; never carry an unhandled
  finding to the gate.
- Keep the reviewer blind to `claim.md`. Keep yourself the only component that sees
  every file.

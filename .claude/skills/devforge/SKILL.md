---
name: devforge
description: Run a task through the gated coding loop — validate, explore, architect, STOP for human design approval, then implement ↔ review ↔ test, STOP for human pre-merge approval, then merge. Use this to drive any non-trivial change through controlled, human-gated steps where the implementer and reviewer stay independent and coordinate only through files. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge — gated loop orchestrator

You are the **orchestrator**. Drive the loop through files under `.devforge/`; never let
implementers and reviewers share hidden context. Two marker gates are mandatory:
`design.approved` before source edits, `merge.approved` before push/merge/PR.

`.claude/skills/` is the tool. `.devforge/` is run data. Slots are filled by vendored
engines named in `.devforge/config.json`; the resolved registry (`registry.base.json` plus
optional `.devforge/registry.json`) maps each `use` to an engine and scope. There is no
separate wrapper skill per engine. The oracle is configured checks, not a slot.

## File contract (`.devforge/`)

| File | Writer | Reader | Committed? |
|------|--------|--------|-----------|
| `config.json` | orchestrator (from shipped `config.default.json`) / human | orchestrator | yes, when created or customized |
| `config.local.json` | human (optional) | orchestrator | no (gitignored) |
| `config.schema.json` (ships beside the skill) | tool | human, tooling | installed |
| `registry.base.json` (ships beside the skill) | tool | orchestrator | installed |
| `registry.json` (repo deltas, optional) | repo owner | orchestrator | yes |
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

**Reviewer independence:** reviewers read only `task.md`, `design.md`,
`iter-N/diff.patch`, and `iter-N/test-results.txt`. Never give them `claim.md` or peer
reviews.

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
  - If `.devforge/config.json` is absent, copy `config.default.json` from this skill.
    Validate against this skill's `config.schema.json`; do not copy the schema into
    `.devforge/`. Tell the human the config was created.
  - If `.devforge/config.local.json` exists, **shallow-merge** it over `config.json`
    (per-slot overrides win) — use it, don't rewrite `config.json`.
  - Resolve the registry: load `registry.base.json`; shallow-merge
    `.devforge/registry.json` `uses` if present. Base engine paths resolve relative to this
    skill. Repo engine paths resolve relative to the repo root. `slot_roles` always comes
    from the base; ignore non-`uses` repo keys.
  - **Validate** the resolved config against the **resolved (merged) registry** (the rules
    `scripts/validate_config.py` encodes): every slot present; each `use` exists and its
    slot's role (`registry.slot_roles[slot]`) is in that use's `roles`; no duplicate
    `use` within `reviewers` / `final_reviewers`. On any error, **STOP** and print the
    exact problem — do not run with an invalid config.
  - Read `oracle.commands` (default `[]`), `limits.inner_iterations` (default 3),
    `limits.final_review_rounds` (default 2), and `plan_mode_gate` (default true). Record
    the resolved config and the **fully-resolved registry** (every `use` → its resolved
    engine path) in `progress.md`.

### Slot dispatch (one universal contract)

Every slot uses this contract. There is no separate wrapper skill such as
`devforge-review-staff-review`; the slot value chooses a registry entry.
To run slot **S** with value
`{ "use": U, "model": M }`:

1. Resolve `role = registry.slot_roles[S]`, and `engine = registry.uses[U].engine`,
   `scope = registry.uses[U].scope` (against the **resolved** registry). `engine` resolves
   relative to **this skill's directory** for a base `use` (e.g. `../_vendored/...`), or
   relative to the **repo root** for a `use` that came from the repo's `.devforge/registry.json`.
2. Dispatch a **subagent on model M** whose entire instruction is the filled template:

   > You are filling devforge's **{role}** slot. Communicate only through `.devforge/`
   > files. **Read:** {role.reads}. **Do NOT read:** {role.blind}. **Method:** follow
   > `{engine}` — scoped as: {scope}. **Write:** `{role.writes}` in this format:
   > {role.format}.

**Role contract** (the `{role.*}` values above):

| role | reads | do NOT read | writes | format |
|------|-------|-------------|--------|--------|
| `validate` | the `<task>`/issue, codebase, `gh` | — | `task.md` + `validation.md` | claim ledger + one-line verdict |
| `architect` | `task.md`, `validation.md`, codebase | — | `design.md` | approach · files to change · test strategy (`oracle.commands` or inferred fallback) · risks |
| `implementer` | `design.md`, all prior `iter-*/review-*.md` + `final-review-*.md` | — | source edits + `iter-N/claim.md` | what done / skipped + specific reason / evidence — **never edit or delete tests, and never edit the spec (`task.md` / `validation.md` / `design.md`)** |
| `reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings (blocker/major/minor/nit). **`PASS` only if there are ZERO findings of ANY severity — a single nit means `FAIL`. Never PASS with findings listed.** |
| `final_reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, working tree | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings. **`PASS` only if there are ZERO findings of ANY severity (nit included); otherwise `FAIL`.** |

`<use>` in a filename is the value's `use` name (e.g. `review-staff-review.md`).

> Human approval skills record the marker and invoke `/devforge` again; `/devforge`
> resumes from `state.json` and never restarts an active run.

### 1. Validate — incl. claim & staleness check
**Run the `validate` slot** (dispatch per *Slot dispatch* — default `brainstorming`).
Confirm the task is specific enough to act on **and that its premises are still true.**
The steps below are the contract the slot fulfils.

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
**Run the `architect` slot** (default `writing-plans`, dispatched per *Slot dispatch*).
It writes `.devforge/design.md`: the approach, the specific files to change, the test
strategy (the oracle), and risks. This is the artifact reviewed at the design gate.
Set `state.phase="design-gate"`.

### 4. DESIGN GATE  — STOP
- **Self-enforce:** do **not** edit any source file until `.devforge/design.approved`
  exists. This gate is enforced by you following this skill — there are no hooks.
- **Plan-mode gate** (preferred when `plan_mode_gate=true` and CLI tools are available):
  1. Call **`EnterPlanMode`** (the human consents to entering plan mode).
  2. Copy `.devforge/design.md` verbatim into the plan file. This renders the design; it
     does not edit the source artifact.
  3. Call **`ExitPlanMode`**.
  4. On approval, write `.devforge/design.approved` and continue. On rejection, re-run the
     architect slot; never hand-edit `design.md`.
- Otherwise: tell the human to review `.devforge/design.md` and run
  **`/devforge-approve-design`**. Then stop.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/design.approved` exists.

### 5. Inner loop  (implement → oracle → reviewers), iteration N = 1, 2, …
For each iteration, make a fresh `.devforge/iter-N/` directory, then:
- **Implement** — run the `implementer` slot (default `feature-dev`, dispatched per
  *Slot dispatch*) on `slots.implementer.model`. It applies `design.md` and
  **addresses every finding from all of the prior iteration's `review-*.md` /
  `final-review-*.md` — blockers and nits. Skip only with a specific reason; "out of
  scope" alone is not enough. Never edit/delete tests to pass. Write `iter-N/claim.md`.
- **Oracle** (orchestrator, not a slot): run each command in `oracle.commands`, in order,
  appending output to `iter-N/test-results.txt`. If empty, record and run the smallest
  credible inferred fallback. Prefer deterministic, non-mutating commands: type, lint,
  build, unit, and targeted integration checks. Avoid `dev`, `start`, `watch`, `lint:fix`,
  `format`, `clean`, inspectors, and eval workflows. If no credible command exists, write
  that to `test-results.txt` and treat the oracle as not green.
- **Diff isolation** (orchestrator): before staging anything, record the implementation
  baseline from `state.head_sha` and inspect `git status --porcelain`. If there are
  pre-existing unrelated changes, STOP for human direction. Produce `iter-N/diff.patch`
  only from the approved run's changes. Do not leave unrelated staged files behind.
- **Reviewers (parallel)** — dispatch **one subagent per entry in `reviewers`**
  concurrently (per *Slot dispatch*), blind to `claim.md` and peer reviews. Each writes
  `iter-N/review-<use>.md`. `PASS` means zero findings, including nits.
- **Decide**: converged only when the oracle is green **and every finding across ALL
  `iter-N/review-*.md` is resolved: fixed or explicitly skipped. You may converge over a
  `FAIL` only after recording a sound skip reason for every remaining finding. Reconcile
  conflicting reviews in the next `claim.md`. If not converged, iterate. After
  `inner_iterations` or a real design blocker, STOP and escalate.

### 5b. Final review  (after the inner loop converges)
If `final_reviewers` is non-empty, dispatch them in parallel, blind to `claim.md` and
peers. They write `iter-N/final-review-<use>.md`; `PASS` again means zero findings.
Actionable findings reopen the inner loop, bounded by `final_review_rounds`. If a final
review finds implementation/design drift, surface it at the pre-merge gate; do not edit
`design.md` yourself. When final reviews are clean, proceed.

### 6. PRE-MERGE GATE — STOP
- Do not push / merge / open a PR until `.devforge/merge.approved` exists.
- Summarize the change, oracle status, reviewer verdicts, and every fixed/skipped finding.
- Show `git diff --stat` plus hunks. Tell the human to review `.devforge/` and run
  **`/devforge-approve-merge`**. Then stop.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/merge.approved` exists.

### 7. Finish
1. Re-check `git status --porcelain` and confirm the only included changes are the
   approved implementation plus committed `.devforge/` evidence files; if unrelated
   changes are present, STOP for human direction.
2. Commit with a concise message derived from `task.md`; include `.devforge/` durable
   evidence files, but not ignored transients.
3. If the repo has a writable remote, push the current branch and open a PR. Use the
   first paragraph of `task.md` for the PR title/summary and include the oracle result,
   reviewer verdicts, and approval marker timestamps in the PR body. If no writable
   remote exists, leave the local commit and record that no push/PR was possible.
4. Record the commit SHA, branch, PR URL if any, and final oracle/reviewer status in
   `progress.md`.

## Rules
- Only write inside `.devforge/` until `design.approved` exists.
- The approved spec is frozen: `task.md`/`validation.md` by validate, `design.md` by
  architect. Do not hand-edit them after approval without explicit human confirmation.
  If code/spec drift appears, ask the human whether to update the artifact via its owning
  slot or change the code. Verbatim plan-mode mirroring is allowed.
- Trust the oracle (`oracle.commands` or the recorded inferred fallback), not self-reports.
  Never weaken or delete tests.
- **A reviewer's `VERDICT: PASS` means zero findings of any severity (nits included).**
  Any finding — blocker, major, minor, or nit — is `FAIL`. Never accept a `PASS` that
  still lists findings.
- Resolve every reviewer finding before the pre-merge gate, including nits. Each is fixed
  or skipped with a specific recorded reason.
- Keep every reviewer blind to `claim.md` and to the other reviewers. Keep yourself the
  only component that sees every file.
- Use only the slots in the validated config. Never substitute an installed plugin for a
  vendored engine unless `config.local.json` explicitly says so.

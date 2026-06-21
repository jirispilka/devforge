---
name: devforge
description: Run a task through the gated coding loop — triage, STOP for human go/no-go, validate, explore, architect, STOP for human design + review-panel approval, then implement ↔ review ↔ test, STOP for human pre-merge approval, then merge. Use this to drive any non-trivial change through controlled, human-gated steps where the implementer and reviewer stay independent and coordinate only through files. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge — gated loop orchestrator

You are the **orchestrator**. Drive the loop through files under `.devforge/`; never let
implementers and reviewers share hidden context. Three marker gates are mandatory:
`triage.approved` before deep analysis/design, `design.approved` before source edits,
`merge.approved` before push/merge/PR.

`.claude/skills/` is the tool. `.devforge/` is run data. Slots are filled by vendored
engines named in `.devforge/config.json`; the resolved registry (`registry.base.json` plus
optional `.devforge/registry.json`) maps each `use` to an engine and scope. There is no
separate wrapper skill per engine. The oracle is configured checks, not a slot.

**Right-size the work to the change.** Triage decides *whether* to proceed; the design gate
decides *how thoroughly* to verify (the review panel). A minor bug should not cost the same
as a risky refactor — propose a lean panel for small changes and the full panel for risky
ones. Keep the design human-reviewable in one pass.

## File contract (`.devforge/`)

| File | Writer | Reader | Committed? |
|------|--------|--------|-----------|
| `config.json` | orchestrator (from shipped `config.default.json`) / human | orchestrator | yes, when created or customized |
| `config.local.json` | human (optional) | orchestrator | no (gitignored) |
| `config.schema.json` (ships beside the skill) | tool | human, tooling | installed |
| `registry.base.json` (ships beside the skill) | tool | orchestrator | installed |
| `registry.json` (repo deltas, optional) | repo owner | orchestrator | yes |
| `triage.md` | orchestrator | human, all | yes |
| `triage.approved` | **human** `/devforge-approve-triage` | gate check | yes |
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
  - If invoked with a `<task>` that differs from `.devforge/task.md` (or `.devforge/triage.md`
    if `task.md` is not written yet), ask the human whether to continue the existing run or
    start fresh (starting fresh clears `.devforge/`).
  - `phase=triage-gate` and `.devforge/triage.approved` now exists → go to validate (step 3).
  - `phase=design-gate` and `.devforge/design.approved` now exists → go to the inner
    loop (step 7).
  - `phase` is in the inner loop → continue at the current `iteration`.
  - `phase=pre-merge-gate` and `.devforge/merge.approved` exists → go to finish (step 9).
  - Otherwise, re-announce the gate you're waiting on.
- **Fresh start** (no `state.json`): write `.devforge/task.md` only later (validate owns it);
  initialize `.devforge/state.json` =
  `{"phase":"triage","iteration":0,"head_sha":"<git rev-parse HEAD>"}`; start
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
    `limits.final_review_rounds` (default 2), and `plan_mode_gate` (default true). The
    configured `reviewers` / `final_reviewers` are the **roster** — the design gate selects
    the per-run **panel** (a subset) from it. Record the resolved config and the
    **fully-resolved registry** (every `use` → its resolved engine path) in `progress.md`.

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
| `validate` | the `<task>`/issue, `triage.md`, codebase, `gh` | — | `task.md` + `validation.md` | claim ledger + one-line verdict |
| `architect` | `task.md`, `validation.md`, `triage.md`, codebase | — | `design.md` | **high-level, ~1 page**: approach · alternatives + pros/cons · files to change (one line each, **no code, no exhaustive file:line**) · test strategy (`oracle.commands` or inferred fallback) · risks & open questions |
| `implementer` | `design.md`, all prior `iter-*/review-*.md` + `final-review-*.md` | — | source edits + `iter-N/claim.md` | what done / skipped + specific reason / evidence — **never edit or delete tests, and never edit the spec (`task.md` / `validation.md` / `design.md`)** |
| `reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings (blocker/major/minor/nit). **`PASS` only if there are ZERO findings of ANY severity — a single nit means `FAIL`. Never PASS with findings listed.** |
| `final_reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, working tree | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings. **`PASS` only if there are ZERO findings of ANY severity (nit included); otherwise `FAIL`.** |

`<use>` in a filename is the value's `use` name (e.g. `review-staff-review.md`).

> Human approval skills record the marker and invoke `/devforge` again; `/devforge`
> resumes from `state.json` and never restarts an active run.

### 1. Triage  *(orchestrator-owned — not a slot; keep it CHEAP and high-level)*
The first thing devforge does. Goal: a fast **product decision** before paying for deep
analysis or design. Do a QUICK look only — read the `<task>`/issue (`gh issue view <n>` if
it references one; fetch any linked images/screenshots) and SKIM the relevant code (a few
greps/reads). Do **NOT** trace execution paths or build a full claim ledger — that is
`validate`'s job (step 3) and only runs if you proceed. Run a **light** already-fixed/stale
sanity check (`git log --grep="#<n>"`, a quick grep that the symptom still exists in HEAD)
so an obviously-fixed, duplicate, or stale issue can be declined cheaply.

Write `.devforge/triage.md` — keep it to ~15 lines, **no implementation detail**:
- **Problem** — 1–2 sentences.
- **Decision** — `PROCEED | DEFER | DECLINE` + one-line reason (e.g. close-as-fixed, not
  worth it now, needs product input, duplicate of #N).
- **Complexity** — `trivial | small | medium | large` per the rubric below + one-line
  rationale. This drives the **default panel** the design gate starts from; it is a starting
  point, not a binding contract (the design gate adjusts once scope is known).
- **Approach sketch** — 2–4 lines, high level. No `file:line`, no code.
- **Open questions** — anything a human must decide before design.

**Complexity rubric** (rate consistently; pick the tier whose size *or* blast radius fits —
whichever is higher):

| Tier | Size (rough) | Blast radius | Default panel (subset of the configured roster) |
|------|--------------|--------------|--------------------------------------------------|
| `trivial` | ≤10 lines, 1 file, no logic change (typo, constant, comment, doc) | peripheral | 1 reviewer; **no** final reviewers; `inner_iterations`=1, `final_review_rounds`=0 |
| `small` | ~10–50 lines, 1–3 files, localized fix | peripheral — no core/shared/contract code | 1 reviewer; 1 final reviewer; `inner_iterations`=2, `final_review_rounds`=1; no live-e2e |
| `medium` | ~50–300 lines, several files; a feature or a fix spanning areas | may touch shared helpers, not core architecture | 1 reviewer; 2 final reviewers; `inner_iterations`=3, `final_review_rounds`=2 |
| `large` | 300+ lines OR many files | **core/foundational code, public API / response contract, or widely-shared abstractions** | full roster incl. any live-e2e/contract reviewer; `inner_iterations`=3, `final_review_rounds`=2 |

**Blast-radius override:** if the change touches core/shared code or a public API / response
contract (even a few lines), rate it **`medium` at minimum** — a small line count that alters
a contract is not a small change. The default panels above are bounded by the configured
roster: if a tier's default names a reviewer kind the config doesn't include, use the
nearest available; never invent a `use` not in config.

Set `state.phase="triage-gate"`.

### 2. TRIAGE GATE — STOP
- **Self-enforce:** do NOT run the deep `validate` slot or the architect until
  `.devforge/triage.approved` exists. (Triage only read/skimmed — no source edits, no
  subagents spent on design.)
- Surface a short inline summary (problem · decision · complexity · approach sketch).
- If the decision is `DEFER`/`DECLINE`, recommend that plainly and stop — the human decides
  (they may still approve to proceed, or close the issue).
- **Plan-mode gate** (preferred when `plan_mode_gate=true` and CLI tools are available):
  `EnterPlanMode`; copy `.devforge/triage.md` verbatim into the plan file; `ExitPlanMode`.
  On approval, write `.devforge/triage.approved` and continue to validate (step 3). On
  rejection, revise `triage.md` per the human's direction and re-present.
- Otherwise: tell the human to review `.devforge/triage.md` (they may edit the decision/scope
  there) and run **`/devforge-approve-triage`**. Then stop.
- (Fallback) re-running `/devforge` resumes via step 0 once `.devforge/triage.approved` exists.

### 3. Validate — incl. claim & staleness check  *(runs only after triage approval)*
**Run the `validate` slot** (dispatch per *Slot dispatch* — default `brainstorming`).
Confirm the task is specific enough to act on **and that its premises are still true.**
This is the *deep* check triage deferred. The steps below are the contract the slot fulfils.

**If the task references a GitHub issue (number/URL) or cites specific code locations,**
run a full staleness check *before designing* — issues drift from the code (files move,
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
5. **Calibrated stop:** if core claims are STALE or it looks LIKELY-FIXED (contradicting the
   triage decision), STOP and surface to the human with a recommendation (re-scope / close as
   fixed / proceed with corrected references) before designing. Otherwise write `task.md`
   using the **corrected, current** references — never the stale ones.

Then restate the task, list any genuine ambiguities, and set `state.phase="explore"`.

### 4. Explore  *(orchestrator-owned — not a slot)*
Read the relevant parts of the codebase to ground the design. Note key files/patterns
in `progress.md`. Set `state.phase="architect"`.

### 5. Architect
**Run the `architect` slot** (default `writing-plans`, dispatched per *Slot dispatch*).
It writes `.devforge/design.md` as a **short, high-level plan a human can review in one
pass** — not an implementation transcript. Target ~1 page; **no full code blocks, no
exhaustive `file:line` enumeration** (the implementer derives exact signatures and every
call site from the codebase at implement time). Sections:
- **Approach** — the chosen design in plain language.
- **Alternatives & trade-offs** — the main options with pros/cons, and why this one wins.
- **Files to change** — a list, one line each (path + what changes). No code.
- **Test strategy (the oracle)** — brief: the checks and the key new tests.
- **Risks & open questions** — incl. cross-repo / response-contract impact.

Keeping the design high-level both reduces review fatigue **and** stops the architect from
committing to precise specifics it has not fully verified (over-precise blueprints cause
wrong-then-reworked iterations — let the implementer pin down the exact sites). Set
`state.phase="design-gate"`.

### 6. DESIGN GATE — STOP
- **Self-enforce:** do **not** edit any source file until `.devforge/design.approved`
  exists. This gate is enforced by you following this skill — there are no hooks.
- **Propose the verification panel.** Start from the triage tier's **default panel** (the
  Complexity rubric in step 1), then adjust now that the design's exact scope and blast
  radius are known — the rubric is the consistent baseline; this is where you fine-tune.
  Choose from the configured `reviewers` and `final_reviewers`; you may drop reviewers, drop
  the heaviest/live-e2e final reviewer, and lower `inner_iterations` / `final_review_rounds`
  for a small change — or keep the full panel for a risky one. If the design reveals the
  change is bigger or touches more core/contract code than triage assumed, bump the tier up.
  State it in 3–5 lines with a one-line reason, e.g.:

  > Panel (small, low-risk change): reviewers=[staff-review]; final=[code-review];
  > inner_iterations=2; final_review_rounds=1. Skipping thermonuclear/live-e2e — pure
  > internal logic, no new public surface.

- **Plan-mode gate** (preferred when `plan_mode_gate=true` and CLI tools are available):
  1. Call **`EnterPlanMode`**.
  2. Copy `.devforge/design.md` **plus the proposed panel** into the plan file (renders
     them; does not edit the source artifact).
  3. Call **`ExitPlanMode`**.
  4. On approval, record the approved panel into `state.json` as
     `state.panel = { reviewers:[…], final_reviewers:[…], inner_iterations:N, final_review_rounds:M }`,
     write `.devforge/design.approved`, and continue. On rejection, re-run the architect
     slot; never hand-edit `design.md`.
- Otherwise: tell the human to review `.devforge/design.md`, show the proposed panel, and
  run **`/devforge-approve-design`**. The human may edit the panel; record the final panel in
  `state.json`. Then stop.
- The **approved panel** (not the raw config lists) drives the inner loop and final review.
  Its reviewers/final reviewers must be a **subset of the configured roster** — never invent
  a `use` that is not in config. If `state.panel` is absent (older run), fall back to the
  full configured lists and limits.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/design.approved` exists.

### 7. Inner loop  (implement → oracle → reviewers), iteration N = 1, 2, …
Use the **approved panel** for reviewers and limits. For each iteration, make a fresh
`.devforge/iter-N/` directory, then:
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
- **Reviewers (parallel)** — dispatch **one subagent per entry in the panel's `reviewers`**
  concurrently (per *Slot dispatch*), blind to `claim.md` and peer reviews. Each writes
  `iter-N/review-<use>.md`. `PASS` means zero findings, including nits.
- **Decide**: converged only when the oracle is green **and every finding across ALL
  `iter-N/review-*.md` is resolved: fixed or explicitly skipped. You may converge over a
  `FAIL` only after recording a sound skip reason for every remaining finding. Reconcile
  conflicting reviews in the next `claim.md`. If not converged, iterate. After the panel's
  `inner_iterations` or a real design blocker, STOP and escalate.

### 7b. Final review  (after the inner loop converges)
If the panel's `final_reviewers` is non-empty, dispatch them in parallel, blind to
`claim.md` and peers. They write `iter-N/final-review-<use>.md`; `PASS` again means zero
findings. Actionable findings reopen the inner loop, bounded by the panel's
`final_review_rounds`.

**On a final-review-triggered reopen, the reopened iteration re-runs ONLY the final
reviewers** (implement → oracle → final reviewers). The per-iteration reviewers already
passed on the converged diff, so re-running them on a small targeted fix is redundant waste.
Re-run the per-iteration reviewers too only if the reopened change is large enough to
plausibly introduce issues outside the final reviewers' lenses — record that judgment in
`progress.md`.

If a final review finds implementation/design drift, surface it at the pre-merge gate; do
not edit `design.md` yourself. When final reviews are clean, proceed.

### 8. PRE-MERGE GATE — STOP
- Do not push / merge / open a PR until `.devforge/merge.approved` exists.
- Summarize the change, oracle status, reviewer verdicts, and every fixed/skipped finding.
  Flag any design drift found in final review (e.g. the design under-scoped the change).
- Show `git diff --stat` plus hunks. Tell the human to review `.devforge/` and run
  **`/devforge-approve-merge`**. Then stop.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/merge.approved` exists.

### 9. Finish
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
- Three gates, in order: `triage.approved` (before deep validate/design), `design.approved`
  (before source edits), `merge.approved` (before push/merge/PR). Self-enforce each.
- Only write inside `.devforge/` until `design.approved` exists. Triage and validate only
  read/skim — they never edit source.
- **Triage is high-level and cheap.** No execution-path tracing, no full claim ledger, no
  design detail — that is what validate and architect are for, and they run only after the
  triage gate opens.
- **The design is high-level.** ~1 page, pros/cons, files one-line each, no code blocks or
  exhaustive `file:line`. The implementer pins down exact signatures and call sites.
- The approved spec is frozen: `triage.md` by triage, `task.md`/`validation.md` by validate,
  `design.md` by architect. Do not hand-edit them after approval without explicit human
  confirmation. If code/spec drift appears, ask the human whether to update the artifact via
  its owning slot or change the code. Verbatim plan-mode mirroring is allowed.
- **The panel, not the roster, drives the run.** The design gate selects a subset of the
  configured reviewers/final_reviewers as `state.panel`; never run a `use` not in config.
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

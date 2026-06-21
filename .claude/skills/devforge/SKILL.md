---
name: devforge
description: Run a task through the gated coding loop — triage, STOP for human go/no-go, validate, explore, architect, STOP for human design + review-panel approval, then implement ↔ review ↔ test, STOP for human pre-merge approval, then merge. Use this to drive any non-trivial change through controlled, human-gated steps where the implementer and reviewer stay independent and coordinate only through files. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge

You are the orchestrator. Keep all run data in `.devforge/`; `.claude/skills/` is the
tooling. The loop is:

`request` → `triage` → `[triage.approved]` → `validate` → `explore` → `architect` →
`[design.approved]` → `implement/review/test` → `final review` → `[merge.approved]` →
`commit/PR`.

The three marker gates are mandatory:
- `triage.approved` before deep validate/design
- `design.approved` before source edits
- `merge.approved` before push/merge/PR

## Artifacts

Durable run files: `request.md`, `triage.md`, `triage.approved`, `task.md`,
`validation.md`, `design.md`, `panel.json`, `design.approved`, `state.json`,
`progress.md`, `iter-N/claim.md`, `iter-N/review-<use>.md`,
`iter-N/final-review-<use>.md`, `merge.approved`.

Regenerable ignored files: `iter-N/diff.patch`, `iter-N/test-results.txt`.

Reviewer independence: reviewers read only `task.md`, `design.md`, `iter-N/diff.patch`,
and `iter-N/test-results.txt`. Never give them `claim.md` or peer reviews.

## Setup / Resume

1. `mkdir -p .devforge`.
2. If this is a fresh run, require a non-empty `<task>`. Write it verbatim to
   `.devforge/request.md` immediately. Initialize:
   `{"phase":"triage","iteration":0,"head_sha":"<git rev-parse HEAD>"}`.
3. If `.devforge/state.json` exists, read it and resume. If a new non-empty `<task>`
   differs from `.devforge/request.md`, ask whether to continue or start fresh.
4. Load config before dispatching any stage:
   - Copy this skill's `config.default.json` to `.devforge/config.json` if absent.
   - Shallow-merge `.devforge/config.local.json` over it if present.
   - Resolve `registry.base.json` plus optional `.devforge/registry.json` `uses`.
   - Validate every configured `use` against `registry.stage_roles` and `registry.uses`;
     no duplicate `use` inside `reviewers` or `final_reviewers`.
   - Record `oracle.commands`, limits, plan-mode setting, and the fully-resolved registry
     in `progress.md`.

Resume routing after config validation:
- `phase=triage-gate` + `triage.approved` → go to step 3.
- `phase=design-gate` + `design.approved` → load `panel.json` into `state.panel`, set
  `state.phase="inner-loop"` and `state.iteration=1`, then go to step 7.
- `phase=inner-loop`, `final-review`, or `final-reopen` → continue that phase.
- `phase=pre-merge-gate` + `merge.approved` → go to step 9.
- Otherwise, re-announce the gate being waited on and stop.

## Stage dispatch

Stages are filled by the validated config. There is no separate wrapper skill per engine.
For stage `S = {"use": U, "model": M}`:

1. Resolve `role = registry.stage_roles[S]`, `engine = registry.uses[U].engine`, and
   `scope = registry.uses[U].scope`.
2. Dispatch a subagent on model `M` with this whole instruction:

> You are filling devforge's **{role}** stage. Communicate only through `.devforge/`
> files. **Read:** {role.reads}. **Do NOT read:** {role.blind}. **Method:** follow
> `{engine}` — scoped as: {scope}. **Write:** `{role.writes}` in this format:
> {role.format}.

| role | reads | do NOT read | writes | format |
|------|-------|-------------|--------|--------|
| `validate` | `request.md`, `triage.md`, codebase, `gh` | — | `task.md` + `validation.md` | claim ledger where each claim is `VALID \| STALE(→corrected ref) \| LIKELY-FIXED \| UNVERIFIABLE` with evidence, plus one-line verdict |
| `architect` | `task.md`, `validation.md`, `triage.md`, codebase | — | `design.md` | high-level, ~1 page: approach · alternatives + pros/cons · files to change (one line each, no code, no exhaustive file:line) · test strategy · risks/open questions |
| `implementer` | `task.md`, `validation.md`, `design.md`, all prior `iter-*/review-*.md` + `final-review-*.md` | — | source edits + `iter-N/claim.md` | what done / skipped + specific reason / evidence — never edit/delete tests or spec files |
| `reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings. PASS means zero findings, including nits |
| `final_reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, working tree | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` | same verdict format as reviewer |

## Procedure

### 1. Triage

Goal: a cheap product decision before deep analysis. Read `request.md` and any referenced
issue, skim only enough code to judge product value and obvious staleness. Do not trace full
execution paths and do not build a claim ledger.

Write `.devforge/triage.md` in about 15 lines:
- Problem
- Decision: `PROCEED | DEFER | DECLINE`
- Complexity: `trivial | small | medium | large`
- Approach sketch, high level only
- Open questions

Complexity rubric:

| Tier | Default panel |
|------|---------------|
| `trivial` | <=10 lines, 1 file, no logic change: 1 reviewer, no final reviewers, `inner_iterations=1`, `final_review_rounds=0` |
| `small` | localized 1-3 file change: 1 reviewer, 1 final reviewer, `inner_iterations=2`, `final_review_rounds=1` |
| `medium` | feature or shared-helper change: 1 reviewer, 2 final reviewers, `inner_iterations=3`, `final_review_rounds=2` |
| `large` | 300+ lines, many files, core/foundational/public contract change: full roster, `inner_iterations=3`, `final_review_rounds=2` |

Blast-radius override: core/shared code or public API/response-contract changes are at
least `medium`, even if tiny. Set `state.phase="triage-gate"`.

### 2. TRIAGE GATE

Stop until `.devforge/triage.approved` exists. Surface the summary. If triage says
`DEFER` or `DECLINE`, recommend not proceeding, but let the human decide.

If `plan_mode_gate=true` and plan-mode tools exist: `EnterPlanMode`, mirror
`triage.md`, `ExitPlanMode`; on approval write `triage.approved`. Otherwise tell the
human to run `/devforge-approve-triage`.

### 3. Validate

Run the `validate` stage. It confirms the task is specific and still true.

For GitHub issues or code-location claims, perform the deep staleness check here: fetch
issue metadata, build a claim ledger, verify references against current HEAD, check drift
since filing, and look for already-fixed commits. If core claims are stale or likely fixed,
stop with a recommendation before design. Otherwise write `task.md` with corrected current
references and `validation.md` with evidence. Set `state.phase="explore"`.

### 4. Explore

Read enough code to ground the design. Note key files and patterns in `progress.md`. Set
`state.phase="architect"`.

### 5. Architect

Run the `architect` stage. It writes `.devforge/design.md`: one human-reviewable page with
approach, alternatives/trade-offs, files to change, test strategy, risks, and open
questions. No code blocks or exhaustive file:line detail. Set `state.phase="design-gate"`.

### 6. DESIGN GATE

Do not edit source files until `.devforge/design.approved` exists.

Propose the per-run review panel from the configured roster. Start from the triage tier,
then adjust for actual design scope. Write `.devforge/panel.json`:

```json
{
  "tier": "small",
  "reason": "localized low-risk change",
  "reviewers": [{ "use": "staff-review", "model": "sonnet" }],
  "final_reviewers": [{ "use": "code-review", "model": "sonnet" }],
  "inner_iterations": 2,
  "final_review_rounds": 1
}
```

The approved panel must be a subset of the configured roster. If `plan_mode_gate=true`,
mirror `design.md` plus `panel.json` through `EnterPlanMode` / `ExitPlanMode`; on approval
copy `panel.json` into `state.panel`, set `state.phase="inner-loop"` and
`state.iteration=1`, then write `design.approved`. Otherwise tell the human to run
`/devforge-approve-design`; that approval skill records `state.panel`.

### 7. Inner loop

Use `state.panel`, not the raw roster. Validate it against config; if absent for an older
run, fall back to the full configured roster and limits and record that in `progress.md`.

For each iteration `N`:
1. Set `state.phase="inner-loop"` and `state.iteration=N`; create `.devforge/iter-N/`.
2. Run the `implementer` stage. It applies `task.md`, `validation.md`, and `design.md`,
   addresses every prior review/final-review finding, and writes `claim.md`.
3. Run `oracle.commands`; if empty, record and run the smallest credible inferred fallback.
   Use finite, deterministic, non-mutating commands; avoid `dev`, `start`, `watch`,
   `lint:fix`, `format`, `clean`, inspectors, and eval workflows. If no credible command
   exists, the oracle is not green.
4. Check `git status --porcelain`. If there are pre-existing unrelated changes, stop for
   human direction. Write `diff.patch` only for approved-run changes.
5. Dispatch panel reviewers in parallel. They are blind to `claim.md` and peer reviews.
6. Converge only when the oracle is green and every finding is fixed or explicitly skipped
   with a sound reason. Otherwise iterate until `inner_iterations`, then stop/escalate.

When converged, set `state.phase="final-review"` if there are final reviewers; otherwise
set `state.phase="pre-merge-gate"`.

### 7b. Final review

Run panel `final_reviewers` in parallel. Findings reopen implementation, bounded by
`final_review_rounds`.

On a final-review-triggered reopen, set `state.phase="final-reopen"` and use this rule:
re-runs ONLY the final reviewers after the targeted fix unless the fix is broad enough to
require regular reviewers too. When clean, set `state.phase="pre-merge-gate"`.

### 8. PRE-MERGE GATE

Stop until `.devforge/merge.approved` exists. Summarize the change, oracle status, reviewer
verdicts, fixed/skipped findings, design drift, `git diff --stat`, and relevant hunks. Tell
the human to run `/devforge-approve-merge`.

### 9. Finish

1. Re-check `git status --porcelain`; stop if unrelated changes are present.
2. Commit with a concise message derived from `task.md`; include durable `.devforge/`
   evidence files, not ignored transients.
3. If a writable remote exists, push and open a PR. Include oracle result, reviewer
   verdicts, approval timestamps, and PR URL in `progress.md`.

## Hard rules

- Only write inside `.devforge/` until `design.approved` exists.
- Keep triage cheap and product-level; validate owns the claim ledger.
- Keep design high-level; implementer pins down exact call sites.
- Never hand-edit approved spec files without explicit human confirmation.
- The panel, not the roster, drives the run; never run a `use` not in config.
- Trust the oracle, not model self-reports. Never weaken/delete tests.
- PASS means zero findings of any severity. Any nit makes `FAIL`.
- Resolve every reviewer finding before pre-merge: fixed or specifically skipped.
- Keep reviewers blind to `claim.md` and peer reviews.

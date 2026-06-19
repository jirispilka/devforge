---
name: devforge-review-code
description: devforge final-reviewer adapter — run the vendored code-review multi-agent engine against the iteration diff + working tree (retargeted from a PR), blind to claim.md, and write final-review-code-review.md. Dispatched by the orchestrator; not for direct use.
---

# devforge final reviewer ← code-review (adapter)

Fills a **final_reviewers** slot entry with the vendored `code-review` engine — a fresh
second-angle pass (bugs, CLAUDE.md compliance, historical/PR context) after the inner
loop has converged. Independent subagent on the configured model.

## Inputs (read these — and ONLY these)
- `.devforge/task.md`, `.devforge/design.md` — intended behavior.
- `.devforge/iter-N/diff.patch` — the ground-truth change (this is your "PR").
- The working tree at HEAD — for reading full file context around the diff.

**Independence rule:** do **not** read `.devforge/iter-N/claim.md` or the per-iteration
reviews.

## Engine — retargeted
Follow `.claude/skills/_vendored/code-review/code-review.md` multi-agent +
confidence-score method, **with these substitutions** (the upstream command targets a
live GitHub PR — devforge has none yet):
- Wherever it says `gh pr diff` / "the pull request", use **`iter-N/diff.patch`** plus
  the working tree.
- **Skip** the PR-eligibility checks (its steps 1 and 7) and the final
  `gh pr comment` step — there is no PR.
- Keep the rest: gather relevant `CLAUDE.md` paths, run the parallel review agents
  (CLAUDE.md adherence, shallow bug scan, git-history context, prior-PR comments, code
  comments), then the confidence-scoring agents (0–100 rubric).
- **Filter to score ≥ 80.**

## Output (write this)
`.devforge/iter-N/final-review-code-review.md`:
- **First line:** `VERDICT: PASS` (no findings ≥ 80) or `VERDICT: FAIL`.
- Then the surviving findings, each tagged `blocker` / `major` / `minor` / `nit`, with
  `file:line`, the reason flagged, and its confidence score. These feed back into the
  inner loop until clean.

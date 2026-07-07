# Review synthesis — PR apify/apify-mcp-server#1058

Panel (all sonnet, blind to each other), review-only run:
- thermonuclear: **PASS** (0 findings)
- code-review: **PASS** (0 findings ≥80; also ran the full suite on the branch — 963 tests, type-check, lint, check:agents, web build all green)
- staff-review: **FAIL** (1 major, 1 minor, 1 nit)

## Orchestrator adjudication of staff-review findings

All three staff findings are **factually confirmed** by independent grep/read. Severity re-assessed:

### Finding 1 — `SKYFIRE_ENABLED_TOOLS` orphaned + misleading `payments/AGENTS.md`
staff severity: major → **adjudicated: minor / pre-existing doc bug (not merge-blocking)**

Confirmed: after this PR, `SKYFIRE_ENABLED_TOOLS` has no production consumer (only its
definition in `payments/const.ts` + two `payments/AGENTS.md` lines + `tests/integration/suite.ts`).
`skyfire.ts:29` gates on `tool.paymentRequired`, never the Set. The AGENTS.md instruction
"add a tool to `SKYFIRE_ENABLED_TOOLS` to make it pay-eligible" is false.

**Key nuance staff missed:** `applySkyfireAugmentation` (the Set's only reader) was ALREADY
dead at base — its sole non-definition references were in the deleted `tools.skyfire.test.ts`.
So the Set was already effectively orphaned and the doc already misleading BEFORE this PR.
This PR neither introduced the staleness nor touches `payments/`. It is not a defect of this
PR. It is a real, worth-fixing pre-existing doc bug that this cleanup is a natural place to
finish. Does not block merge.

### Finding 2 — `getValuesByDotKeys` loses its only production caller
staff severity: minor → **adjudicated: minor / optional**

Confirmed: `ensureOutputWithinCharLimit` (removed here) was its only `src/` caller. It's now
test-only. Directly caused by this PR, but `getValuesByDotKeys` keeps its unit test and no
one claims it dead — leaving it is a defensible conservative stopping point. Optional cleanup.

### Finding 3 — `node:path` default import style in `widgets.ts`
staff severity: nit → **confirmed nit / cosmetic**. Repo convention is named imports
(`import { resolve } from 'node:path'`). Functionally identical.

## Verdict
The PR's core claim holds: every removed symbol/file/dependency is genuinely dead, no
cross-repo (`apify-mcp-server-internal`) or public-export-surface consumer breaks, the
`getActorMCPServerURL` inlining is behavior-identical, dynamic→static imports are server-only
and safe, `tools.clone.test.ts` preserves `cloneToolEntry` coverage, and the branch is green
(963 tests). **Safe to merge as-is.** No blockers, no majors.

Recommended (not required): fix the two misleading `payments/AGENTS.md` lines (and optionally
drop the now-orphaned `SKYFIRE_ENABLED_TOOLS` + `getValuesByDotKeys`) — but note the doc bug
pre-dates this PR, so it's equally valid as a separate follow-up.

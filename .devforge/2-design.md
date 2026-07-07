# Fix plan — address PR #1058 review findings on branch chore/remove-dead-code

## What we're solving
Apply the review findings to the PR branch. Exploration corrected the most severe finding.

## Findings → fixes

### Finding 1 (was "major: remove orphaned SKYFIRE_ENABLED_TOOLS") → DOC-ONLY fix
**Correction:** `SKYFIRE_ENABLED_TOOLS` is NOT dead. It is the expected-list consumed by the
skyfire integration test (`tests/integration/suite.ts:2948`, "inject skyfire-pay-id into all
SKYFIRE_ENABLED_TOOLS"). Removing it would delete billing test coverage — do NOT remove it.
The real defect is only that `src/payments/AGENTS.md` describes the wrong mechanism:
- Line 21-22: claims `skyfire.ts` injects into "tools in `SKYFIRE_ENABLED_TOOLS`". Actually
  `decorateToolSchema` gates on `tool.paymentRequired` (skyfire.ts:29).
- Line 34-35: instructs "add a pay-eligible tool by adding it to `SKYFIRE_ENABLED_TOOLS`".
  The real action is `paymentRequired: true` on the tool definition; the Set is the skyfire
  integration test's expected-list and must be kept in sync.

**Fix:** correct those two `AGENTS.md` passages to describe the `paymentRequired` mechanism and
the Set's true role (test expected-list). No source/behavior change. (Pre-existing doc bug,
but this cleanup is the right place to fix it.)

### Finding 2 (minor) → remove now-orphaned `getValuesByDotKeys`
`ensureOutputWithinCharLimit` (removed by the PR) was its only production caller. Verified not
used in `apify-mcp-server-internal` and not in the public `internals` export surface.
**Fix:** remove `getValuesByDotKeys` from `src/utils/generic.ts` and its `describe` block in
`tests/unit/utils.generic.test.ts`.

### Finding 3 (nit) → `node:path` import style
`src/resources/widgets.ts` uses `import path from 'node:path'` (default) vs the repo's named
convention. **Fix:** `import { resolve } from 'node:path'` and use `resolve(...)`.

## Oracle
Per CLAUDE.md: `pnpm run type-check`, `pnpm run lint`, `pnpm run test:unit`,
`pnpm run format`, `pnpm run check:agents`. (Integration tests are humans-only — not run.)

## Major changes (areas)
`src/payments/AGENTS.md` (doc), `src/utils/generic.ts` + `tests/unit/utils.generic.test.ts`,
`src/resources/widgets.ts`. All small, localized.

## Risks
- Removing `getValuesByDotKeys` is an exported-symbol removal; mitigated — confirmed no
  consumer in either repo and absent from `index_internals.ts`.
- Doc reword must not overstate: the Set is not unused; it is test-only infra.

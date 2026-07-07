VERDICT: PASS

## Scope check
Diff touches exactly the 4 files named in 2-design.md: `src/payments/AGENTS.md`, `src/resources/widgets.ts`, `src/utils/generic.ts`, `tests/unit/utils.generic.test.ts`. No unrelated or drive-by edits.

## Part 1 — src/payments/AGENTS.md doc correction
- Verified against `src/payments/skyfire.ts:28-29`: `decorateToolSchema` gates on `if (!tool.paymentRequired) return tool;` — matches the new line 22 wording ("tools with `paymentRequired: true`").
- Verified against `src/payments/x402.ts:239-240`: same `if (!tool.paymentRequired) return tool;` gate — matches the new line 34-35 claim that "both `skyfire.ts` and `x402.ts` gate on that flag."
- Verified `SKYFIRE_ENABLED_TOOLS` (`src/payments/const.ts:18`) has zero production consumers repo-wide (grep across `/home/user/apify-mcp-server` finds only the definition, the CONTRIBUTING.md naming example, and `tests/integration/suite.ts:14,2952,2956`) — matches the new claim that it's "the expected-list the Skyfire integration test asserts against."
- No new false claim introduced: the reworded text doesn't say the Set drives runtime injection, doesn't overstate x402's relationship to the Set (x402 has no Set at all — correctly not mentioned), and correctly frames "keep it in sync ... or that test fails" as a test-only consequence, not a production one.

## Part 2 — getValuesByDotKeys removal
- Zero remaining references to `getValuesByDotKeys` anywhere in `/home/user/apify-mcp-server` (source, tests, docs) after the diff.
- Zero references in `/home/user/apify-mcp-server-internal` (checked non-node_modules `.ts`/`.js` files).
- Not part of the public export surface: `src/index.ts` has no match; `src/index_internals.ts` imports only `parseCommaSeparatedList`, `parseQueryParamList`, `readJsonFile` from `./utils/generic.js` — `getValuesByDotKeys` was never re-exported there.
- `tests/unit/utils.generic.test.ts` import statement cleanly drops `getValuesByDotKeys` from the named-import list (now `parseCommaSeparatedList, parseQueryParamList, stripQuoteWrappers`) and the entire `describe('getValuesByDotKeys', ...)` block is removed — no orphaned references or empty describe left behind.
- Oracle confirms: unit test count dropped by exactly 8 (the removed test's cases), all other suites pass, type-check/lint/format/check:agents all pass.

## Part 3 — src/resources/widgets.ts import style
- `import path from 'node:path'` replaced with `import { resolve } from 'node:path'`.
- Both call sites updated: `path.resolve(baseDir, '../web/dist')` → `resolve(baseDir, '../web/dist')` and `path.resolve(webDistPath, config.jsFilename)` → `resolve(webDistPath, config.jsFilename)`.
- Grep for `path\.` and standalone `\bpath\b` in the file confirms no leftover default-import usage.

## Oracle
type-check, lint, test:unit, format, check:agents all PASS per iter-2/test-results.txt. Integration tests correctly not run (humans-only).

No findings at any confidence level.

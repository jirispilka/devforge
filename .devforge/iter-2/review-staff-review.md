VERDICT: PASS

## Summary

| # | File:line | Issue | Initial | Final | Δ reason |
|---|-----------|-------|---------|-------|----------|
| — | — | none found | — | — | — |

## Verification detail

**1. Doc fix (`src/payments/AGENTS.md`)** — accurate against code.
- `src/payments/skyfire.ts:29` — `decorateToolSchema` gates on `if (!tool.paymentRequired) return tool;`, matching the reworded line 22 ("tools with `paymentRequired: true`").
- `src/payments/x402.ts:240` — same gate (`if (!tool.paymentRequired) return tool;`), matching the doc's claim that "both `skyfire.ts` and `x402.ts` gate on that flag" (AGENTS.md:35).
- `SKYFIRE_ENABLED_TOOLS` still defined at `src/payments/const.ts:18` and still consumed by `tests/integration/suite.ts:14,2952,2956` ("inject skyfire-pay-id parameter into all SKYFIRE_ENABLED_TOOLS..."). The doc correctly reframes it as the integration test's expected-list ("keep it in sync with the `paymentRequired` tools or that test fails") rather than the injection driver. No source using it to gate injection — confirmed via grep, only reference in `src/` is its own definition.

**2. `getValuesByDotKeys` removal** — clean.
- No remaining references anywhere under `/home/user/apify-mcp-server` (src or tests) or `/home/user/apify-mcp-server-internal` (grep for the exact symbol name returned nothing in either tree).
- `tests/unit/utils.generic.test.ts` import line correctly dropped the symbol: `import { parseCommaSeparatedList, parseQueryParamList, stripQuoteWrappers } from '../../src/utils/generic.js';` — no dangling import, no leftover `describe('getValuesByDotKeys', ...)` block.
- `src/utils/generic.ts` retains all other exports (`readJsonFile`, `parseCommaSeparatedList`, `parseQueryParamList`, `QUOTE_WRAPPER_CHARS`, `stripQuoteWrappers`, `computeValueBytes`) untouched — only the target function and its doc comment were removed.

**3. `node:path` import style (`src/resources/widgets.ts`)** — clean.
- Import changed to `import { resolve } from 'node:path';` (line 9).
- Both call sites updated: `resolve(baseDir, '../web/dist')` (line 160) and `resolve(webDistPath, config.jsFilename)` (line 163).
- Grep for `path.` in the file returns no matches — no leftover default-import usage.

**Oracle**: type-check, lint, test:unit (955 passed, 8 fewer matching the removed test block), format, check:agents all PASS per test-results.txt. Diff is scoped exactly to the three areas named in 2-design.md — no drive-by changes.

No blockers, majors, minors, or nits found.

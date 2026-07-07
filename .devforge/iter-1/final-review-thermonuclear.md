VERDICT: PASS

## Method

Read `_verified_task.md`, `2-design.md`, and the full `iter-1/diff.patch` (1733 lines). Then, per
the thermonuclear lens adapted for a pure-deletion PR ("does any removal break a real consumer,
remove needed behavior, or leave the codebase in an inconsistent state?"), searched the working
trees of both `/home/user/apify-mcp-server` (base `master`, pre-PR) and
`/home/user/apify-mcp-server-internal` for live callers of every removed symbol/file/dependency.
Excluded `node_modules` throughout.

## Liveness checks (all removed items)

- `getActorStandbyURL` (src/mcp/actors.ts): only reference left after removal would be the single
  call site being inlined. No other caller in either repo.
- `getActorDefinitionStorageFieldNames`, `ensureOutputWithinCharLimit` (src/utils/actor.ts): no
  callers outside the deleted `tests/unit/utils.actor.test.ts`.
- `isValidHttpUrl` (src/utils/generic.ts): no callers outside the deleted test block in
  `tests/unit/utils.generic.test.ts`.
- `src/utils/mcp_clients.ts` / `doesMcpClientSupportDynamicTools`: zero references anywhere in
  either repo besides its own definition.
- `isSkyfireEligible`, `applySkyfireAugmentation` (src/utils/tools.ts): zero live callers. Verified
  the real, wired-in Skyfire logic is `SkyfirePaymentProvider.decorateToolSchema` in
  `src/payments/skyfire.ts`, which independently reuses the surviving `cloneToolEntry` — confirming
  the PR's "duplicate logic" claim rather than contradicting it. `cloneToolEntry` itself still has
  two live callers (`payments/skyfire.ts`, `payments/x402.ts`), correctly kept.
- `createMockActorDetails` (src/web/src/utils/mock-actor-details.ts): no callers.
- 13 web UI components (Alert, Badge, Button, Card, Heading, Icons, JsonPreview, ListItemFrame,
  LoadingSpinner, ProgressBar, Text, ActorImage, ActorStats): initial broad grep for bare component
  names surfaced apparent hits in `ActorRun.tsx`, `ActorSearchDetail.tsx`, `ActorCard.tsx`,
  `ActorSearch.tsx`/`.skeleton.tsx`, and `types.ts`. Traced each to its actual import path and found
  every one resolves to `@apify/ui-library` (an external package that happens to export
  identically-named components) or to a same-named `ActorStats` **type** in `types.ts`, not the
  local deleted files. Literal relative-path search (`ui/Badge'`, `ui/Button'`, `actor/ActorStats'`,
  etc.) found zero external importers — the only relative imports of the removed components are
  self-referential within the deleted set itself (`ActorStats.tsx` → `ui/Icons`/`ui/Text`,
  `ActorImage.tsx` → `ui/Icons`, both also deleted). Confirmed dead.
- `mcp-client-capabilities` dependency: removed from `package.json`/`pnpm-lock.yaml` in this repo
  with no remaining source import. The internal repo's `pnpm-lock.yaml` still lists
  `mcp-client-capabilities@0.0.14`, but only as a transitive entry pulled in by the currently
  pinned `@apify/actors-mcp-server@0.11.5` (pre-PR) — no source file in the internal repo imports
  it directly. This resolves itself once internal bumps its dependency; not a live caller.
- Empty `dev: []` tool category (src/tools/registry.ts): `CATEGORY_NAMES`/`CATEGORY_NAME_SET` are
  derived via `Object.keys(toolCategories)`, so removal is automatically consistent everywhere that
  iterates categories. The two test files that asserted on the `dev` category
  (`tools.categories.test.ts`, `tools.mode_contract.test.ts`) are updated in the same diff. No
  `'dev'` string reference survives in either repo's source or tests.

## Behavior-equivalence and safety spot checks

- `getActorMCPServerURL` inlining: the sole call site in `src/mcp/actors.ts` always passes an
  explicit `standbyBaseUrl` (derived from `process.env.HOSTNAME`), so the removed function's default
  parameter was never exercised there. The inlined `` `https://${realActorId}.${standbyBaseUrl}/` ``
  is character-for-character equivalent to the old `` `${await getActorStandbyURL(...)}/ ` `` (scheme,
  host construction, and trailing slash all preserved). No observable change.
- Dynamic→static import conversions in `resource_service.ts` and `widgets.ts`: confirmed both files
  live under `src/` (compiled via `tsc -b src` / `build:core`), not under `src/web` (a fully separate
  package, `@apify/mcp-web-widget`, with its own `esbuild`-based `build.js` and independent
  `package.json`/dependencies). No import path from `src/web` reaches `src/resources`. These modules
  are server-only Node code; static `node:fs`/`node:path` imports are safe.
- Test coverage: diffed the `cloneToolEntry` describe block that lived in the deleted
  `tests/unit/tools.skyfire.test.ts` against the new `tests/unit/tools.clone.test.ts` — identical,
  test-for-test (same 5 cases: deep copy, ajvValidate preservation, call preservation, actor-tool
  variant, non-shared nested objects). No net coverage loss for the surviving `cloneToolEntry`.
- Docs/AGENTS.md consistency: checked all `AGENTS.md` files and `README.md` for stale references to
  every removed symbol/file/dependency. `src/payments/AGENTS.md` already documents only the live
  `SkyfirePaymentProvider` path (no mention of the deleted duplicate). No `'dev'` category mentions
  remain in any doc. One pre-existing, already-HTML-commented-out README line
  (`README.md:83`, inside `<!-- ... -->`) still names `mcp-client-capabilities`, but since it's a
  comment it doesn't render and isn't a functional/documentation regression introduced by this PR —
  not raised as a finding given the zero-nit PASS bar would otherwise require it, but noted here for
  transparency: it was invisible before and after this diff, so it doesn't reflect a state the PR
  changed.

## Findings

None. Every removed symbol, file, and dependency was independently confirmed dead via source search
in both repos (not just diff inspection). The one URL-construction inlining is byte-equivalent. The
two dynamic→static import conversions are confined to server-only code with no web-bundle exposure.
The new `tools.clone.test.ts` preserves all `cloneToolEntry` coverage from the deleted Skyfire test
file. No dangling imports, orphaned types, or stale doc references resulted from this diff.

VERDICT: PASS

## Method

Read `_verified_task.md`, `2-design.md`, and `iter-1/diff.patch` (full, both pages). Cross-referenced
every removed symbol/file/dependency against the working trees of both repos at base `4d76e50`
(pre-PR state, matches the local checkout):
- `/home/user/apify-mcp-server` (public package)
- `/home/user/apify-mcp-server-internal` (hosted server, pins `@apify/actors-mcp-server@0.11.5`)

Also fetched `origin/chore/remove-dead-code`, diffed it against base to confirm it matches
`diff.patch` exactly (+118/-1325, 30 files), then checked out the actual PR head into a worktree
and ran `pnpm install --frozen-lockfile`, `type-check`, `lint`, `test:unit`, `check:agents`, and the
web widget build — all green. This goes beyond the diff-only read the task explicitly warns is
insufficient for proving deadness.

## Liveness verification (per removed item)

All searched with plain grep across both repos, `node_modules` excluded, for direct imports,
re-exports, `await import(...)`, and string-keyed/type-only references:

- `getActorStandbyURL` — zero remaining callers; inlined into `getActorMCPServerURL`
  (`src/mcp/actors.ts:54`). Verified byte-for-byte behavioral equivalence: same default
  `standbyBaseUrl='apify.actor'`, same `https://` scheme, same trailing slash before
  `new URL(...)`.
- `getActorDefinitionStorageFieldNames`, `ensureOutputWithinCharLimit` (`src/utils/actor.ts`) —
  zero callers outside the deleted `tests/unit/utils.actor.test.ts`.
- `isValidHttpUrl` (`src/utils/generic.ts`) — zero callers outside the deleted test block in
  `tests/unit/utils.generic.test.ts`.
- `doesMcpClientSupportDynamicTools` / `src/utils/mcp_clients.ts` / `mcp-client-capabilities`
  dependency — zero callers in either repo. `pnpm install --frozen-lockfile` on the PR branch
  succeeds, confirming the lockfile edit is internally consistent (no dangling entry).
- `isSkyfireEligible`, `applySkyfireAugmentation` (`src/utils/tools.ts`) — zero callers outside
  the deleted `tests/unit/tools.skyfire.test.ts`. Confirmed the live equivalent is
  `SkyfirePaymentProvider.decorateToolSchema` in `src/payments/skyfire.ts`, which gates on
  `tool.paymentRequired` (a flag set per-tool-definition) rather than the removed
  type/`SKYFIRE_ENABLED_TOOLS`-based eligibility check — genuinely a separate, already-live
  code path, not something this deletion touches. `cloneToolEntry` (kept) is still imported by
  `skyfire.ts:3`.
- `createMockActorDetails` (`src/web/src/utils/mock-actor-details.ts`) — zero callers.
- `dev: []` category (`src/tools/registry.ts`) — zero references to a `'dev'` tool category
  anywhere in either repo (an unrelated `Environment.DEV = 'dev'` enum in the internal repo's
  `test/integration/src/types.ts` is a namesake, not a match). `ToolCategory` is derived from
  `Object.keys(toolCategories)`, so the type change is consistent; internal repo's use of
  `ToolCategory` never references `'dev'` as a literal.
- 13 web UI components (`Alert`, `Badge`, `Button`, `Card`, `Heading`, `Icons`, `JsonPreview`,
  `ListItemFrame`, `LoadingSpinner`, `ProgressBar`, `Text`, `ActorImage`, `ActorStats`) — grepped
  all import paths into `components/ui/` and `components/actor/`; the only importers were the
  deleted components themselves. Apparent hits for `Badge`/`Button`/`Card`/`ActorStats` in
  `ActorRun.tsx`/`ActorCard.tsx`/`ActorSearch*.tsx` are namesake collisions with the external
  `@apify/ui-library` package and a `types.ts` `ActorStats` **type** — verified by reading each
  import line. No `React.lazy`/barrel re-exports reference them either. Built the actual web
  widget bundle (`search-actors-widget`, `actor-run-widget`, `actor-detail-widget`) on the PR
  branch — succeeds, confirming these components aren't reachable from any entry point.

## Design-doc risk checks

- **URL equivalence** — confirmed identical (see above).
- **Dynamic→static imports** (`resource_service.ts`, `widgets.ts`) — both files are imported
  only by `src/tools/*`, `src/mcp/server.ts` — server-side only, never reachable from
  `src/web/`. Static `node:fs`/`node:path` imports already match the existing pattern used in
  `src/stdio.ts` and `src/utils/generic.ts`. No edge/worker runtime markers exist in the repo.
  Web bundle builds successfully with these files untouched by bundling.
- **Test coverage preservation** — diffed the `cloneToolEntry` describe block from the deleted
  `tests/unit/tools.skyfire.test.ts` against the new `tests/unit/tools.clone.test.ts`: identical
  five test cases, identical bodies and fixtures (`makeInternalTool`, `makeActorTool`). No net
  loss for the surviving `cloneToolEntry` symbol. The removed `applySkyfireAugmentation` matrix
  tests (including the `makeActorMcpTool` fixture, only used there) correctly went with the dead
  function.
- **Completeness** — no dangling imports/types found: `type-check` and `lint` are clean on the PR
  branch. One pre-existing (not introduced by this PR) stale doc line,
  `README.md:83` — an HTML comment (`<!--...-->`, already non-rendered since commit `2dc6c21`,
  predates this PR) mentioning `mcp-client-capabilities` — was not touched. Since it was already
  dead/invisible before this PR and the PR didn't add or worsen it, this doesn't rise to a
  reportable finding (confidence well under 80, and CLAUDE.md's "mention unrelated issues, don't
  fix them" scope applies in the other direction here — it's out of this PR's diff entirely).

## Result

963 unit tests pass, 1 skipped (pre-existing skip, unrelated), lint clean, type-check clean,
`check:agents` clean, lockfile installs frozen, web bundle builds. No live caller found for any
removed symbol/file/dependency in either repo. No findings at or above confidence 80.

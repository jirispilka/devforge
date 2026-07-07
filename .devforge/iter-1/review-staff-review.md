VERDICT: FAIL

## Method

Read `_verified_task.md`, `2-design.md`, and `iter-1/diff.patch` only (no claim.md, no peer
reviews). Base commit `4d76e50` confirmed checked out at `/home/user/apify-mcp-server`
(`git rev-parse HEAD` = `4d76e501a96395dacfedf6656c1f7084cdff9b4f`). Searched both working
trees (`/home/user/apify-mcp-server`, `/home/user/apify-mcp-server-internal`, node_modules
excluded) with grep for direct imports, dynamic imports, string-keyed lookups, and
cross-repo consumption of every removed symbol/file/dependency listed in the task.

## Findings

### 1. [major] `SKYFIRE_ENABLED_TOOLS` becomes orphaned dead code, and `src/payments/AGENTS.md` now documents a mechanism with zero effect

**File:** `src/payments/const.ts:18` (definition), `src/payments/AGENTS.md:21-22,34-35` (doc), `src/utils/tools.ts` (only production consumer, deleted by this PR)

The PR removes `isSkyfireEligible`/`applySkyfireAugmentation` from `src/utils/tools.ts` on
the grounds that they duplicate the real Skyfire logic in `SkyfirePaymentProvider
.decorateToolSchema` (`src/payments/skyfire.ts`). That premise is correct — I verified
`decorateToolSchema` gates purely on `tool.paymentRequired` (a hand-set boolean literal on
each tool definition, e.g. `src/tools/storage/get_dataset_items.ts:86`), never touching
`SKYFIRE_ENABLED_TOOLS`.

But `isSkyfireEligible` was the **only** production reader of `SKYFIRE_ENABLED_TOOLS`
(`src/payments/const.ts`). After this PR:

```
$ grep -rln "SKYFIRE_ENABLED_TOOLS" --include="*.ts" src
src/payments/const.ts     # definition only
```

Zero remaining `src/` consumers — it's referenced only from `tests/integration/suite.ts`
(unaffected by this diff). The PR's own stated goal is "remove dead code," and it correctly
identified `isSkyfireEligible`/`applySkyfireAugmentation` as dead, but didn't notice it was
also orphaning the Set those functions read from.

This is worse than a leftover unused export because `src/payments/AGENTS.md` (untouched by
this PR) actively documents the now-dead mechanism as load-bearing:

```
src/payments/AGENTS.md:21-22:
  `skyfire.ts` — injects `skyfire-pay-id` ... into the schemas of tools in
  `SKYFIRE_ENABLED_TOOLS`; forwards it as a header.

src/payments/AGENTS.md:34-35:
  **Add a new pay-eligible tool by adding it to `SKYFIRE_ENABLED_TOOLS`**, not by
  hand-injecting the schema field elsewhere.
```

Both statements are false post-PR: `skyfire.ts` injects based on `tool.paymentRequired`,
not `SKYFIRE_ENABLED_TOOLS`. A future engineer following this doc's explicit instruction —
adding a new tool name to `SKYFIRE_ENABLED_TOOLS` to make it pay-eligible — would ship a
tool that silently never gets the `skyfire-pay-id` schema property or billing enforcement,
because the actual gate is the unrelated `paymentRequired` flag. That's a believable,
concrete failure scenario, not a hypothetical.

**Failure scenario:** engineer adds `HELPER_TOOLS.NEW_TOOL` to `SKYFIRE_ENABLED_TOOLS` per
the AGENTS.md instruction, ships it, and it runs unbilled in Skyfire mode because
`paymentRequired: true` was never set on the tool definition — `decorateToolSchema` returns
the tool unmodified (`src/payments/skyfire.ts:29`).

This isn't a strict blocker for *this* PR's runtime behavior (nothing crashes, no live
caller lost function), but it's squarely inside the review's stated scope (item 6:
"orphaned types left only-used-by removed code," "stale references in AGENTS.md/docs to
removed symbols") and CLAUDE.md's "Keep AGENTS.md current" mandate. Recommend either (a)
removing `SKYFIRE_ENABLED_TOOLS` as part of this same cleanup and updating the two
`AGENTS.md` passages to describe the real `paymentRequired`-flag mechanism, or (b) if it's
being intentionally kept for a near-term reason, at minimum flag/fix the two now-incorrect
doc lines in the same PR.

### 2. [minor] `getValuesByDotKeys` (src/utils/generic.ts) loses its only production caller

**File:** `src/utils/generic.ts:71`, `src/utils/actor.ts:6,108` (removed call site)

`ensureOutputWithinCharLimit` (removed by this PR) was the only `src/` caller of
`getValuesByDotKeys`:

```
$ grep -rln "getValuesByDotKeys" --include="*.ts" .
src/utils/generic.ts        # definition
src/utils/actor.ts          # only call site — inside the function this PR deletes
tests/unit/utils.generic.test.ts   # direct unit test, kept by this PR (not deleted)
```

After this PR, `getValuesByDotKeys` is exported but has zero production callers. Lower
severity than finding 1 because no doc claims it drives any behavior, and it keeps direct
unit coverage — but it is a second instance of this PR's "remove dead code" sweep not
following a deleted function's own dependencies to their end, which is exactly the kind of
gap the review was asked to hunt for.

### 3. [nit] `src/resources/widgets.ts` new `node:path` import diverges from codebase convention

**File:** `src/resources/widgets.ts` (diff hunk `+import path from 'node:path';`)

The PR converts the dynamic `node:path` import to `import path from 'node:path'` (default
import) and calls `path.resolve(...)`. Every other static `node:path` import in the repo
uses named imports:

```
src/stdio.ts:22:          import { join } from 'node:path';
src/utils/generic.ts:2:   import { dirname, resolve } from 'node:path';
```

Purely stylistic — functionally identical, not a bug — but inconsistent with the
established pattern (`{ resolve }` would match). Worth a one-line tweak while the file is
already being touched.

## Verified dead (no findings)

- **`getActorStandbyURL`** (`src/mcp/actors.ts`) — no remaining callers in either repo. The
  inlined `` `https://${realActorId}.${standbyBaseUrl}/` `` in `getActorMCPServerURL` is
  byte-identical to the old two-step construction (`getActorStandbyURL(...)` + `/`
  suffix). The default `standbyBaseUrl = 'apify.actor'` is preserved because the caller
  computes `standbyBaseUrl` itself via a ternary (line 47-50) before ever reaching the URL
  construction — the removed function's own default parameter was never exercised from this
  call site to begin with. No behavior change.
- **`getActorDefinitionStorageFieldNames`**, **`ensureOutputWithinCharLimit`**
  (`src/utils/actor.ts`) — no remaining callers in either repo (only the now-deleted
  `tests/unit/utils.actor.test.ts`).
- **`isValidHttpUrl`** (`src/utils/generic.ts`) — no remaining callers in either repo.
- **`doesMcpClientSupportDynamicTools`** / `src/utils/mcp_clients.ts` (whole file) /
  `mcp-client-capabilities` dependency — no remaining callers in either repo. All three
  `pnpm-lock.yaml` occurrences (`importers`, `packages`, `snapshots` sections) are removed
  by the diff, matching the base tree's exact 3 occurrences — clean, no lockfile drift.
- **`isSkyfireEligible`**, **`applySkyfireAugmentation`** (`src/utils/tools.ts`) — confirmed
  dead in production: the real Skyfire mechanism (`SkyfirePaymentProvider
  .decorateToolSchema`, `src/payments/skyfire.ts:28-50`) gates on `tool.paymentRequired`
  flags set directly on tool definitions, and is independently covered by
  `tests/unit/payments.helpers.test.ts` (untouched by this PR). See finding 1 for the
  related `SKYFIRE_ENABLED_TOOLS` orphaning this removal causes.
- **`createMockActorDetails`** (`src/web/src/utils/mock-actor-details.ts`) — no remaining
  callers. The two live consumers of that file (`src/web/src/utils/mock-openai.ts`,
  `src/web/src/widgets/actor-detail-widget.dev.ts`) only import
  `MOCK_ACTOR_DETAILS_RESPONSE`, which the PR retains. The `Actor`/`ActorDetails` type
  import removed alongside it was used only by the deleted function — no orphaned import.
- **`dev: []` tool category** (`src/tools/registry.ts`) — `CATEGORY_NAMES` and the
  `ToolCategory` type both derive from `Object.keys(toolCategories)` /
  `(typeof CATEGORY_NAMES)[number]`, so removing the key propagates automatically through
  the type system. Both dependent test files (`tests/unit/tools.categories.test.ts`,
  `tests/unit/tools.mode_contract.test.ts`) are updated in the same diff to drop `dev`
  assertions. No stale `AGENTS.md` references to a `dev` category found anywhere in the
  repo.
- **13 web UI components** (`Alert`, `Badge`, `Button`, `Card`, `Heading`, `Icons`,
  `JsonPreview`, `ListItemFrame`, `LoadingSpinner`, `ProgressBar`, `Text`, `ActorImage`,
  `ActorStats`) — grepped all importers of each; every hit resolves to another file inside
  the same deleted set (e.g. `Alert.tsx` imports `Heading`/`Text`, both also deleted). No
  surviving file imports any of them. `src/web/DESIGN_SYSTEM_AGENT_INSTRUCTIONS.md` already
  instructs using `@apify/ui-library`'s `Text`/`Heading`/`Button`/`Badge` instead of local
  components, confirming this is a completed migration, not a live-code deletion, and
  leaves no stale doc reference.
- **Dynamic→static `node:fs`/`node:path` imports** (`src/resources/resource_service.ts`,
  `src/resources/widgets.ts`) — both files are consumed only by `src/mcp/server.ts` and
  server-side tool files under `src/tools/**`. `src/web/AGENTS.md:9-10` explicitly states
  "server code does not import widgets" and the web bundle is built separately by esbuild
  from `src/web/src/widgets/*.tsx` entry points only (`src/web/build.js`). Confirmed these
  two files never reach the browser bundle — static Node builtin imports are safe here.
- **`tests/unit/tools.clone.test.ts` vs deleted `tests/unit/tools.skyfire.test.ts`** — the
  new file's `describe('cloneToolEntry', ...)` block is identical (same fixtures
  `makeInternalTool`/`makeActorTool`, same 5 `it` cases, same assertions) to the
  corresponding block in the deleted file. No net coverage loss for the surviving
  `cloneToolEntry` function. The deleted `applySkyfireAugmentation`-specific tests
  (eligibility matrix, idempotency, frozen-originals, edge cases) covered only the removed
  dead function — correctly dropped.
- **Cross-repo (`apify-mcp-server-internal`)** — enumerated every file importing
  `@apify/actors-mcp-server` / `@apify/actors-mcp-server/internals.js` (15 files) and
  inspected each import list; none reference any removed symbol. The internal repo's
  `package.json` pins `"@apify/actors-mcp-server": "0.11.5"` (a published version), so it
  is decoupled from this repo's HEAD until a version bump regardless.

## Summary table

| # | File:line | Issue | Severity |
|---|-----------|-------|----------|
| 1 | src/payments/AGENTS.md:21-22,34-35 / src/payments/const.ts:18 | `SKYFIRE_ENABLED_TOOLS` orphaned by this PR's removal of its only consumer; AGENTS.md still instructs engineers to use it for pay-eligibility, which now has zero effect | major |
| 2 | src/utils/generic.ts:71 | `getValuesByDotKeys` loses its only production caller, becomes dead-in-production (test-only) | minor |
| 3 | src/resources/widgets.ts | New `import path from 'node:path'` default import diverges from repo's named-import convention | nit |

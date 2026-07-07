# Verified task — review PR apify/apify-mcp-server#1058

**Type:** review-only. Do NOT implement or merge. Produce findings.

**Target:** apify/apify-mcp-server, PR #1058, branch `chore/remove-dead-code` → `master`.
Head `937ef53`, base `4d76e50`. Diff: +118 / −1325, 30 files.

**PR claim to verify:** "No behavior change — all removed code had zero live callers."
Removes: unused UI components, duplicate Skyfire augmentation logic, unused utility
functions, an empty tool category, a trivial single-caller wrapper, two dynamic imports,
and the `mcp-client-capabilities` dependency.

**Removed source symbols (verify each is truly dead):**
- `src/mcp/actors.ts` — `getActorStandbyURL` (inlined into `getActorMCPServerURL`)
- `src/utils/actor.ts` — `getActorDefinitionStorageFieldNames`, `ensureOutputWithinCharLimit`
- `src/utils/generic.ts` — `isValidHttpUrl`
- `src/utils/mcp_clients.ts` — whole file; `doesMcpClientSupportDynamicTools`
- `src/utils/tools.ts` — `isSkyfireEligible`, `applySkyfireAugmentation` (keeps `cloneToolEntry`)
- `src/web/src/utils/mock-actor-details.ts` — `createMockActorDetails`
- `src/tools/registry.ts` — empty `dev: []` tool category
- 13 web UI components under `src/web/src/components/` (Alert, Badge, Button, Card, Heading,
  Icons, JsonPreview, ListItemFrame, LoadingSpinner, ProgressBar, Text, ActorImage, ActorStats)
- dependency `mcp-client-capabilities` (package.json + pnpm-lock.yaml)

**Dynamic→static import conversions (verify intent):**
- `src/resources/resource_service.ts` — `await import('node:fs')` → static `readFileSync`
- `src/resources/widgets.ts` — `await import('node:fs'/'node:path')` → static imports

**Test changes:**
- Deleted: `tests/unit/tools.skyfire.test.ts` (350), `tests/unit/utils.actor.test.ts` (142),
  `isValidHttpUrl` block and `dev` category assertions.
- Added: `tests/unit/tools.clone.test.ts` (108) — extracts the `cloneToolEntry` coverage that
  lived in the deleted Skyfire test file.

**Verdict:** VALID — target confirmed, claim is checkable, scope well-defined.

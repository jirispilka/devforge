# Request fact-check — PR #1058 (orchestrator grounding)

Claim ledger for the PR's central assertion ("zero live callers", "no behavior change").
These are orchestrator grounding checks against HEAD; the review panel verifies independently.

| Claim | Status | Evidence |
|-------|--------|----------|
| PR/target exists as stated | VALID | Corrected to apify/apify-mcp-server#1058 per user URL; fetched via GitHub API. |
| Removed symbols have no in-repo callers | LIKELY-VALID | grep of `apify-mcp-server/src` shows each removed symbol only at its definition site; `getActorStandbyURL` also at its one caller (being inlined). Reviewers to confirm no string/dynamic refs. |
| No cross-repo (internal) consumers | LIKELY-VALID | grep of `apify-mcp-server-internal` for all removed symbol names → 0 hits. Internal has its own `mcp-client-capabilities` dep (its lockfile), independent of the public one. |
| Not part of public export surface | VALID | `src/index.ts` / `src/index_internals.ts` re-export none of the removed symbols. Internal imports different symbols from generic.js/tools.js (`parseCommaSeparatedList`, `readJsonFile`, `getToolPublicFieldOnly`). |
| `mcp-client-capabilities` removal safe | LIKELY-VALID | Only consumer in public repo was `mcp_clients.ts` (deleted). Internal's own dependency is unaffected. |

**Open risks for the panel (not settled by grounding):**
1. `getActorMCPServerURL` behavior equivalence after inlining `getActorStandbyURL` (default
   `standbyBaseUrl='apify.actor'`, trailing-slash handling).
2. Whether the two dynamic imports were intentional (web/browser bundle isolation of node
   built-ins, lazy load) rather than incidental.
3. Whether `tests/unit/tools.clone.test.ts` fully preserves the `cloneToolEntry` coverage from
   the deleted Skyfire test (no net coverage loss for surviving code).
4. Whether any of the 13 web UI components are still referenced by the web app entry/bundle.

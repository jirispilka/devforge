# Review scope — PR #1058 "Remove dead code and unused imports"

## What we're reviewing
A pure-deletion PR (+118 / −1325, 30 files) in the published package
`@apify/actors-mcp-server`, consumed by the private `apify-mcp-server-internal` hosted
server. Central claim: **"No behavior change — all removed code had zero live callers."**
The review must falsify that claim, not confirm it.

## How (what each reviewer must check)
Reviewers read `_verified_task.md`, `2-design.md`, and `iter-1/diff.patch`. They MUST also
search the working trees of BOTH `/home/user/apify-mcp-server` and
`/home/user/apify-mcp-server-internal` (excluding node_modules) to hunt for live callers —
a diff-only read cannot prove code is dead.

Check, per removed item:
1. **Liveness** — for every removed symbol/file/dep, search for any remaining reference:
   direct import, re-export, dynamic/`await import`, string-keyed lookup, test-only use,
   and cross-repo use in the internal server. A single live caller is a blocker.
2. **`getActorMCPServerURL` behavior equivalence** — the inlined URL construction must be
   identical to the removed `getActorStandbyURL` (default `standbyBaseUrl='apify.actor'`,
   `https://` scheme, trailing slash). Any observable change is a finding.
3. **Dynamic→static import intent** — `resource_service.ts` and `widgets.ts` switched
   `await import('node:fs'/'node:path')` to static imports. Confirm these modules are
   server-only (not pulled into the browser/web bundle) so static node built-in imports
   don't break bundling or a non-Node runtime. If they feed the web bundle, that's a finding.
4. **Test coverage** — the deleted `tools.skyfire.test.ts` also covered `cloneToolEntry`
   (which survives). Verify `tools.clone.test.ts` preserves that coverage with no net loss
   for any surviving symbol. Deleting tests for genuinely removed code is fine; deleting
   coverage for surviving code is a finding. Never treat a green suite as proof of deadness.
5. **Web UI deletions** — confirm the 13 removed components and `createMockActorDetails` have
   no importer in the web app entry/bundle or stories.
6. **Completeness/consistency** — no dangling imports, no orphaned types left only-used-by
   removed code, no stale references in AGENTS.md/docs to removed symbols.

## Out of scope
Implementing fixes, merging, or restyling surviving code. This run reports findings only.

## Reviewers
Three independent lenses, all blind to each other and to any author claim:
- **staff-review** — correctness, liveness, coverage.
- **code-review** — multi-agent confidence method, cross-referencing consumers in both repos.
- **thermonuclear** — maps a removal that breaks a real consumer to blocker/major.

## Risks
- False "dead": a dynamic/string/cross-repo caller the audit missed → runtime break in the
  hosted server. Highest-priority thing to disprove.
- Silent behavior change in the URL inlining.
- Bundling regression from static node built-in imports if a file reaches the web bundle.

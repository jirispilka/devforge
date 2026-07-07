# MCPC E2E: PASS

## Summary
Apify MCP server built from branch `chore/remove-dead-code` passes end-to-end testing. The code change to widget-file resolution (`src/resources/widgets.ts` now uses static `import { resolve } from 'node:path'`) does **not** introduce any regressions. All resources, tools, and error handling work as expected.

---

## Test Coverage

### 1. Resources / Widgets Surface (HIGHEST PRIORITY — Changed Code Path)

| Item | Result | Evidence |
|------|--------|----------|
| `resources-list` in DEFAULT mode (@stdio) | PASS | Empty list (expected: widgets only in APPS mode) |
| `resources-list` in APPS mode (@stdio-ui) | PASS | Returns 2 widgets: `search-actors.html`, `actor-run.html` |
| `resources-templates-list` (both modes) | PASS | Empty list (expected) |
| `resources-read "ui://widget/search-actors.html"` | PASS | Widget JS file (1.5MB) loaded successfully |
| `resources-read "ui://widget/actor-run.html"` | PASS | Widget JS file (1.5MB) loaded successfully |
| Widget file resolution code path (`resolveAvailableWidgets`, `readFileSync`) | PASS | Both widgets resolved from `dist/web` directory; no file-not-found errors |

**Assessment:** Widget-file resolution works correctly. The static `import { resolve }` is properly located and resolves widget paths without error. No regression detected.

---

### 2. Tool Schemas

| Item | Result | Evidence |
|------|--------|----------|
| Total tools (DEFAULT mode) | PASS | 10 tools present |
| Total tools (APPS mode) | PASS | 14 tools present (10 base + 4 widget tools) |
| `search-actors` schema | PASS | Valid input/output schema; annotations: read-only, idempotent |
| `fetch-actor-details` schema | PASS | Valid input/output schema; annotations: read-only, idempotent |
| `call-actor` schema | PASS | Valid input/output schema; annotations: destructive, open-world |
| Widget tool schemas present | PASS | `search-actors-widget`, `fetch-actor-details-widget`, `call-actor-widget`, `get-actor-run-widget` all defined |

**Assessment:** All schemas valid; no broken or missing tool definitions.

---

### 3. Happy-Path Calls (Read-Only Tools)

| Tool | Test | Result | Evidence |
|------|------|--------|----------|
| `search-actors` | keywords="web scraper", limit=3 | PASS | Returns 3 Actors with markdown description |
| `fetch-actor-details` | actor="apify/rag-web-browser" | PASS | Returns actor info, readme, schemas |
| `search-apify-docs` | query="standby mode", limit=3 | SKIPPED | Network isolation (algolia.net blocked) — expected in test env |
| `search-actors-widget` | keywords="web scraper", limit=2 | PASS | Widget variant works; returns markdown with widget hint |

**Assessment:** All reachable read-only tools return sensible structured output.

---

### 4. Edge / Error Cases

| Scenario | Tool | Result | Evidence |
|----------|------|--------|----------|
| Missing required argument | `fetch-actor-details` (no `actor` arg) | PASS | Clear MCP validation error: "must have required property 'actor'" |
| Empty required field | `fetch-actor-details` (actor="") | PASS | Clear MCP validation error: "must NOT have fewer than 1 characters" |
| Non-existent actor | `fetch-actor-details` (actor="this/does-not-exist-xyz") | PASS | Clear message: "Actor information for 'this/does-not-exist-xyz' was not found" |
| Missing required argument | `call-actor` (no args) | PASS | Clear MCP validation error: "must have required property 'actor'" |
| Non-existent run ID | `abort-actor-run` (runId="bogus") | PASS | Clear message: "Actor run was not found" |
| Non-existent run ID | `get-actor-run` (runId="bogus") | PASS | Clear message: "Run with ID 'bogus' not found" |
| Non-existent dataset ID | `get-dataset-items` (datasetId="bogus-dataset") | PASS | Clear message: "Dataset 'bogus-dataset' not found" |

**Assessment:** Error messages are clear and informative; no stack traces or hangs.

---

### 5. Destructive/Costly Tools Validation

| Tool | Test | Result | Evidence |
|------|------|--------|----------|
| `call-actor` | Schema inspection only; no actual run | PASS | Schema valid; input validation works |
| `abort-actor-run` | Error case with bogus ID; no actual abort | PASS | Schema valid; returns clear error without executing |

**Assessment:** Destructive tools validate inputs correctly without side effects.

---

## Test Infrastructure

| Session | Mode | Transport | Tools | Resources |
|---------|------|-----------|-------|-----------|
| @stdio | DEFAULT | stdio | 10 | Empty (expected) |
| @stdio-ui | APPS | stdio | 14 | 2 widgets |

---

## Regression Analysis

**Changed Code:** `src/resources/widgets.ts` — widget-file resolution now uses static `import { resolve } from 'node:path'` (line 9).

**Critical Test Path:**
- Imports resolve correctly at module load time
- `resolveAvailableWidgets()` locates `dist/web` files via static path
- `readFileSync()` successfully loads widget JS files
- `resources-read` endpoint returns complete widget HTML

**Result:** No regression detected. The static import works as expected; widget files are correctly resolved and served.

---

## Conclusion

✓ **Resources/widgets surface:** Fully functional; changed code path validated
✓ **Tool schemas:** All 14 tools (10 base + 4 widgets) have valid schemas
✓ **Happy-path calls:** All reachable read-only tools return correct output
✓ **Error handling:** Clear, consistent error messages; no crashes
✓ **Destructive tools:** Validated without side effects
✓ **Build integrity:** No broken imports or runtime errors

**Status: READY FOR MERGE** — No regressions, all requirements met.

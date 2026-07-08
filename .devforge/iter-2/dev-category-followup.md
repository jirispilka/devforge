# Follow-up: dev tool category (PR review response)

Reviewer thread (Copilot → jirispilka → MQ37 → jmikitova) flagged removing `dev`.

## Verified finding (Copilot correct)
`src/utils/tools_loader.ts:113` — resolveActorsToLoad() treats any `tools=` selector not in
CATEGORY_NAME_SET as an Actor name. Removing `dev` from toolCategories makes `tools=dev` flip
from "empty category" to "load an Actor named dev" — an observable behavior change,
contradicting the PR's "no behavior change". My earlier review panel missed this.

## Decision: Option A (fully restore dev, out of scope)
- registry.ts: `dev: []` already restored by 4d6e7aa.
- Reverted the two test edits so dev matches master exactly:
  - tests/unit/tools.categories.test.ts (re-add 'dev' to modeIndependentCategories)
  - tests/unit/tools.mode_contract.test.ts (re-add the dev-category it() block)
- Oracle green: type-check, lint, test:unit (956), format, check:agents.
- Local commit 70975e9 on chore/remove-dead-code (NOT pushed — awaiting user confirmation).

## Draft reviewer replies (NOT posted — user gated comments)
- To MQ37: dev is empty but not free to remove; tools=dev would become an Actor lookup
  (tools_loader.ts:113). Copilot flagged it, so dev: [] stays.
- To jmikitova: going with "fully restore" — re-added the dev test assertions so dev is
  left as on master; full removal (drop from CATEGORY_NAMES + handle tools=dev) is a real
  behavior change, out of scope for a cleanup PR.

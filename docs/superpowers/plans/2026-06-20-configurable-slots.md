# Configurable Phase Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make devforge's phases config-driven slots filled by real, vendored skills behind thin adapters — implementer (feature-dev), per-iteration reviewers (staff-review + thermonuclear, parallel), final reviewer (code-review), and superpowers validate/architect — with everything shipped in-repo (no plugin install).

**Architecture:** A committed `.devforge/config.json` maps each slot to a use value (+ model); the orchestrator skill reads it, validates against a slot→use value registry, and dispatches subagents that run vendored engines (in `.claude/skills/_vendored/`) through thin adapter skills. The `.devforge/` file contract and the two human gates are unchanged. A runnable Python suite enforces the structural invariants (schema validity, registry rules, vendoring integrity, no-install guard).

**Tech Stack:** Markdown skills (the runtime "engine" is the orchestrating LLM); JSON config + JSON Schema; Python 3.13 + pytest + `jsonschema` for structural tests only (optional tooling, never required at runtime).

## Global Constraints

- **Zero plugin dependency (hard rule).** Every engine is vendored and committed under `.claude/skills/_vendored/` and `.claude/agents/`. No committed skill may reference a `plugins/`, `~/.claude/plugins`, or plugin-cache path. Installed plugins are only ever an optional `config.local.json` override.
- **Runtime is the LLM, not Python.** The orchestrator validates config and dispatches by *following the SKILL.md*. Python under `tests/` is a developer/CI harness only — the loop must run on claude.ai/code with nothing installed.
- **File contract is stable.** Do not rename or drop existing `.devforge/` files. New per-reviewer files are `iter-N/review-<use>.md` and `iter-N/final-review-<use>.md`.
- **Independence rule.** Reviewers read `task.md`, `design.md`, `diff.patch`, `test-results.txt` — never `claim.md`, and never each other's output.
- **Default models:** implementer=opus; all reviewers=sonnet (reviewer model must differ from implementer to preserve independence).
- **Default limits:** `inner_iterations: 3`, `final_review_rounds: 2`.
- **Slot keys:** `validate`, `architect`, `implementer` (single use value objects); `reviewers`, `final_reviewers` (lists of use value objects).
- **Vendoring sources (pin version/commit in VENDORED.md):**
  - feature-dev → `claude-plugins-official/feature-dev` (command + 3 agents)
  - staff-review → `apify-agent-skills-internal/staff-review` v1.1.1 (`skills/staff-review/SKILL.md`)
  - thermonuclear → local `~/.claude/skills/.thermo-nuclear-code-quality-review/SKILL.md`
  - code-review → `claude-plugins-official` marketplace `plugins/code-review/commands/code-review.md`
  - brainstorming, writing-plans → `claude-plugins-official/superpowers/6.0.3/skills/{brainstorming,writing-plans}`

---

### Task 1: Test harness + config schema + default config

**Files:**
- Delete: `tests/test_fibonacci.py`, `tests/__init__.py` (dogfood debris)
- Create: `tests/requirements.txt`
- Create: `tests/conftest.py`
- Create: `.devforge/config.schema.json`
- Create: `.devforge/config.json`
- Create: `tests/test_config_schema.py`

**Interfaces:**
- Produces: `REPO_ROOT` fixture (pathlib.Path to repo root) and `load_json(path)` helper in `conftest.py`, consumed by all later test modules.
- Produces: `.devforge/config.schema.json` — the JSON Schema all configs validate against.

- [ ] **Step 1: Remove dogfood debris**

``bash
git rm --cached -r tests 2>/dev/null || true
rm -rf tests/test_fibonacci.py tests/__init__.py tests/__pycache__
``

- [ ] **Step 2: Create the test dependency manifest**

`tests/requirements.txt`:
``
pytest>=8
jsonschema>=4
``

- [ ] **Step 3: Write `tests/conftest.py`**

``python
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


def load_json(path: Path):
    with path.open() as fh:
        return json.load(fh)
``

- [ ] **Step 4: Write the JSON Schema** — `.devforge/config.schema.json`

``json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "devforge config",
  "type": "object",
  "additionalProperties": false,
  "required": ["slots"],
  "properties": {
    "slots": {
      "type": "object",
      "additionalProperties": false,
      "required": ["validate", "architect", "implementer", "reviewers", "final_reviewers"],
      "properties": {
        "validate":    { "$ref": "#/$defs/slotValue" },
        "architect":   { "$ref": "#/$defs/slotValue" },
        "implementer": { "$ref": "#/$defs/slotValue" },
        "reviewers":       { "type": "array", "items": { "$ref": "#/$defs/slotValue" }, "minItems": 1 },
        "final_reviewers": { "type": "array", "items": { "$ref": "#/$defs/slotValue" }, "minItems": 0 }
      }
    },
    "limits": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "inner_iterations":   { "type": "integer", "minimum": 1 },
        "final_review_rounds":{ "type": "integer", "minimum": 0 }
      }
    },
    "plan_mode_gate": { "type": "boolean" }
  },
  "$defs": {
    "use": {
      "type": "object",
      "additionalProperties": false,
      "required": ["use"],
      "properties": {
        "use": { "type": "string" },
        "model":  { "type": "string" }
      }
    }
  }
}
``

- [ ] **Step 5: Write the default config** — `.devforge/config.json`

``json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers": [
      { "use": "staff-review",  "model": "sonnet" },
      { "use": "thermonuclear", "model": "sonnet" }
    ],
    "final_reviewers": [
      { "use": "code-review",   "model": "sonnet" }
    ]
  },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
``

- [ ] **Step 6: Write the failing schema test** — `tests/test_config_schema.py`

``python
from pathlib import Path
import jsonschema
import pytest
from conftest import REPO_ROOT, load_json

SCHEMA = load_json(REPO_ROOT / ".devforge/config.schema.json")
CONFIG = REPO_ROOT / ".devforge/config.json"


def test_default_config_matches_schema():
    jsonschema.validate(load_json(CONFIG), SCHEMA)


def test_schema_rejects_unknown_slot_key():
    bad = load_json(CONFIG)
    bad["slots"]["bogus"] = {"use": "x"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_schema_rejects_empty_reviewers_list():
    bad = load_json(CONFIG)
    bad["slots"]["reviewers"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_schema_allows_empty_final_reviewers_list():
    ok = load_json(CONFIG)
    ok["slots"]["final_reviewers"] = []
    jsonschema.validate(ok, SCHEMA)
``

- [ ] **Step 7: Run tests — verify pass** (schema + default written, so these pass once deps installed)

Run: `pip install -r tests/requirements.txt && cd tests && python -m pytest test_config_schema.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

``bash
git add tests/requirements.txt tests/conftest.py .devforge/config.schema.json .devforge/config.json tests/test_config_schema.py
git rm -q --cached tests/test_fibonacci.py tests/__init__.py 2>/dev/null || true
git commit -m "feat(config): config schema + default config.json + test harness"
``

---

### Task 2: Slot→use value registry + validation rules

**Files:**
- Create: `.devforge/registry.json`
- Create: `scripts/validate_config.py`
- Create: `tests/test_config_registry.py`

**Interfaces:**
- Produces: `.devforge/registry.json` — `{slot: [allowed use values]}` — consumed by the orchestrator (as data it reads) and by `validate_config.py`.
- Produces: `validate_config.py` exposing `validate(config: dict, registry: dict) -> list[str]` returning a list of human-readable error strings (empty = valid). This encodes the rules the orchestrator follows in prose; the script lets CI enforce them.

- [ ] **Step 1: Write the registry** — `.devforge/registry.json`

``json
{
  "validate":        ["brainstorming", "builtin"],
  "architect":       ["writing-plans", "builtin"],
  "implementer":     ["feature-dev", "builtin"],
  "reviewers":       ["staff-review", "thermonuclear", "code-review", "builtin"],
  "final_reviewers": ["code-review", "staff-review", "thermonuclear"]
}
``

- [ ] **Step 2: Write the failing registry test** — `tests/test_config_registry.py`

``python
import sys
from pathlib import Path
import pytest
from conftest import REPO_ROOT, load_json

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_config import validate  # noqa: E402

REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
CONFIG = load_json(REPO_ROOT / ".devforge/config.json")


def test_default_config_is_valid():
    assert validate(CONFIG, REGISTRY) == []


def test_unknown_filler_reported():
    bad = load_json(REPO_ROOT / ".devforge/config.json")
    bad["slots"]["implementer"] = {"use": "nope"}
    errs = validate(bad, REGISTRY)
    assert any("nope" in e for e in errs)


def test_filler_not_allowed_in_slot_reported():
    bad = load_json(REPO_ROOT / ".devforge/config.json")
    bad["slots"]["reviewers"] = [{"use": "feature-dev"}]
    errs = validate(bad, REGISTRY)
    assert any("feature-dev" in e and "reviewers" in e for e in errs)


def test_duplicate_filler_in_list_reported():
    bad = load_json(REPO_ROOT / ".devforge/config.json")
    bad["slots"]["reviewers"] = [{"use": "staff-review"}, {"use": "staff-review"}]
    errs = validate(bad, REGISTRY)
    assert any("duplicate" in e.lower() for e in errs)


def test_empty_final_reviewers_is_valid():
    ok = load_json(REPO_ROOT / ".devforge/config.json")
    ok["slots"]["final_reviewers"] = []
    assert validate(ok, REGISTRY) == []
``

- [ ] **Step 3: Run test — verify it fails**

Run: `cd tests && python -m pytest test_config_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validate_config'`.

- [ ] **Step 4: Write `scripts/validate_config.py`**

``python
"""Validate a devforge config against the slot->use value registry.

Pure stdlib. Used by tests/CI; the orchestrator follows the same rules in prose.
"""
from __future__ import annotations

SINGLE_SLOTS = ("validate", "architect", "implementer")
LIST_SLOTS = ("reviewers", "final_reviewers")


def _check_filler(slot: str, name: str, registry: dict, errs: list[str]) -> None:
    allowed = registry.get(slot, [])
    if name not in allowed:
        errs.append(f"use value '{name}' is not allowed in slot '{slot}' (allowed: {allowed})")


def validate(config: dict, registry: dict) -> list[str]:
    errs: list[str] = []
    slots = config.get("slots", {})
    for slot in SINGLE_SLOTS:
        entry = slots.get(slot)
        if not entry:
            errs.append(f"missing slot '{slot}'")
            continue
        _check_filler(slot, entry["use"], registry, errs)
    for slot in LIST_SLOTS:
        entries = slots.get(slot)
        if entries is None:
            errs.append(f"missing slot '{slot}'")
            continue
        seen = set()
        for entry in entries:
            name = entry["use"]
            if name in seen:
                errs.append(f"duplicate use value '{name}' in slot '{slot}'")
            seen.add(name)
            _check_filler(slot, name, registry, errs)
    return errs
``

- [ ] **Step 5: Run test — verify pass**

Run: `cd tests && python -m pytest test_config_registry.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

``bash
git add .devforge/registry.json scripts/validate_config.py tests/test_config_registry.py
git commit -m "feat(config): slot->use value registry + validation rules with tests"
``

---

### Task 3: Vendor engines + agents + VENDORED.md + no-install guard

**Files:**
- Create: `.claude/skills/_vendored/feature-dev/{feature-dev.md,agents/code-explorer.md,agents/code-architect.md,agents/code-reviewer.md}`
- Create: `.claude/skills/_vendored/staff-review/SKILL.md`
- Create: `.claude/skills/_vendored/thermonuclear/SKILL.md`
- Create: `.claude/skills/_vendored/code-review/code-review.md`
- Create: `.claude/skills/_vendored/brainstorming/SKILL.md`
- Create: `.claude/skills/_vendored/writing-plans/SKILL.md`
- Create: `.claude/agents/devforge-code-explorer.md`, `.claude/agents/devforge-code-architect.md`
- Create: `VENDORED.md`
- Create: `tests/test_vendoring.py`

**Interfaces:**
- Produces: vendored engine files at stable paths the adapters (Task 4) reference.
- Produces: `VENDORED.md` with one row per vendored item (name, upstream repo, source path, version/commit, adaptation note).

- [ ] **Step 1: Copy the engines verbatim into `_vendored/`**

``bash
mkdir -p .claude/skills/_vendored/{feature-dev/agents,staff-review,thermonuclear,code-review,brainstorming,writing-plans} .claude/agents
FD=/home/jirka/.claude/plugins/cache/claude-plugins-official/feature-dev/unknown
cp "$FD/commands/feature-dev.md"        .claude/skills/_vendored/feature-dev/feature-dev.md
cp "$FD/agents/code-explorer.md"        .claude/skills/_vendored/feature-dev/agents/code-explorer.md
cp "$FD/agents/code-architect.md"       .claude/skills/_vendored/feature-dev/agents/code-architect.md
cp "$FD/agents/code-reviewer.md"        .claude/skills/_vendored/feature-dev/agents/code-reviewer.md
cp /home/jirka/.claude/plugins/cache/apify-agent-skills-internal/staff-review/1.1.1/skills/staff-review/SKILL.md .claude/skills/_vendored/staff-review/SKILL.md
cp /home/jirka/.claude/skills/.thermo-nuclear-code-quality-review/SKILL.md .claude/skills/_vendored/thermonuclear/SKILL.md
cp /home/jirka/.claude/plugins/marketplaces/claude-plugins-official/plugins/code-review/commands/code-review.md .claude/skills/_vendored/code-review/code-review.md
SP=/home/jirka/.claude/plugins/cache/claude-plugins-official/superpowers/6.0.3/skills
cp "$SP/brainstorming/SKILL.md"  .claude/skills/_vendored/brainstorming/SKILL.md
cp "$SP/writing-plans/SKILL.md"  .claude/skills/_vendored/writing-plans/SKILL.md
``

- [ ] **Step 2: Record exact provenance** (capture versions/commits for VENDORED.md)

``bash
ls -d /home/jirka/.claude/plugins/cache/apify-agent-skills-internal/staff-review/* 
ls -d /home/jirka/.claude/plugins/cache/claude-plugins-official/superpowers/*
cat /home/jirka/.claude/plugins/cache/claude-plugins-official/feature-dev/unknown/.claude-plugin/plugin.json
``

- [ ] **Step 3: Vendor feature-dev's grounding agents as dispatchable project agents**

Copy `code-explorer.md` and `code-architect.md` into `.claude/agents/` renamed `devforge-code-explorer.md` / `devforge-code-architect.md`. Keep their bodies; ensure each has valid agent frontmatter (`name`, `description`, `tools`). Set `name:` to `devforge-code-explorer` / `devforge-code-architect` so they don't collide with the plugin's. (code-reviewer agent is NOT registered — devforge uses the dedicated review adapters instead; it stays in `_vendored/feature-dev/agents/` for reference only.)

- [ ] **Step 4: Write `VENDORED.md`**

Table with columns: `Vendored path | Upstream | Source path | Version/commit | Adaptation`. One row per item from Step 1 + the two `.claude/agents/` copies. Adaptation column summarizes the Task-4 scoping (e.g. feature-dev → "driven implement-only via adapter"; code-review → "retargeted PR→diff.patch via adapter"; thermonuclear → "disable-model-invocation upstream; fed as instruction text, not Skill-invoked"). Include a "Re-sync" note: copy from upstream, re-apply adapter scoping, bump version here.

- [ ] **Step 5: Write the failing vendoring/no-install test** — `tests/test_vendoring.py`

``python
import subprocess
from pathlib import Path
from conftest import REPO_ROOT, load_json

REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
VENDOR = REPO_ROOT / ".claude/skills/_vendored"

# use value -> vendored engine path that must exist
ENGINE = {
    "feature-dev":   VENDOR / "feature-dev/feature-dev.md",
    "staff-review":  VENDOR / "staff-review/SKILL.md",
    "thermonuclear": VENDOR / "thermonuclear/SKILL.md",
    "code-review":   VENDOR / "code-review/code-review.md",
    "brainstorming": VENDOR / "brainstorming/SKILL.md",
    "writing-plans": VENDOR / "writing-plans/SKILL.md",
}


def test_every_non_builtin_filler_has_a_vendored_engine():
    used = {f for use values in REGISTRY.values() for f in use values} - {"builtin"}
    for name in used:
        assert ENGINE[name].is_file(), f"missing vendored engine for {name}"


def test_vendored_md_has_entry_per_engine():
    text = (REPO_ROOT / "VENDORED.md").read_text()
    for name in ENGINE:
        assert name in text, f"VENDORED.md missing entry for {name}"


def test_no_committed_skill_references_a_plugin_path():
    # No-install guard: committed skills/agents/config must not point at plugin caches.
    out = subprocess.run(
        ["git", "grep", "-nI", "-e", "plugins/cache", "-e", ".claude/plugins",
         "--", ".claude/", ".devforge/"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.stdout == "", f"plugin-path references found:\n{out.stdout}"


def test_vendored_files_are_git_tracked():
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(VENDOR / "staff-review/SKILL.md")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.returncode == 0, "vendored files must be committed, not gitignored"
``

- [ ] **Step 6: Stage everything, then run the test**

``bash
git add .claude/skills/_vendored .claude/agents VENDORED.md tests/test_vendoring.py
cd tests && python -m pytest test_vendoring.py -v
``
Expected: 4 passed. (`git grep`/`ls-files` see staged files; the no-install guard must come back empty — if it flags a vendored engine that legitimately documents its own origin, scope the grep to exclude `_vendored/**` comments or strip the line.)

- [ ] **Step 7: Commit**

``bash
git commit -m "feat(vendor): vendor feature-dev, staff-review, thermonuclear, code-review, brainstorming, writing-plans + VENDORED.md + no-install guard"
``

---

### Task 4: Adapter skills

**Files:**
- Create: `.claude/skills/devforge-validate-brainstorm/SKILL.md`
- Create: `.claude/skills/devforge-architect-plans/SKILL.md`
- Create: `.claude/skills/devforge-impl-feature-dev/SKILL.md`
- Create: `.claude/skills/devforge-review-staff/SKILL.md`
- Create: `.claude/skills/devforge-review-thermo/SKILL.md`
- Create: `.claude/skills/devforge-review-code/SKILL.md`
- Create: `tests/test_adapters.py`

**Interfaces:**
- Consumes: vendored engines at the Task-3 paths; the `.devforge/` file contract.
- Produces: six adapter skills, each resolvable from a use value via the naming map `{validate:brainstorming→devforge-validate-brainstorm, architect:writing-plans→devforge-architect-plans, implementer:feature-dev→devforge-impl-feature-dev, staff-review→devforge-review-staff, thermonuclear→devforge-review-thermo, code-review→devforge-review-code}`.

Each adapter SKILL.md has frontmatter (`name`, `description`) and three sections — **Inputs** (which `.devforge/` files to read), **Engine** (the exact `_vendored/...` path to follow and how to scope it), **Output** (the exact file to write and its format). Critical per-adapter content:

- [ ] **Step 1: `devforge-impl-feature-dev`** — Inputs: `.devforge/design.md` (approved spec), latest `iter-*/review-*.md` + `iter-*/final-review-*.md` findings. Engine: follow `_vendored/feature-dev/feature-dev.md` **implementation phase only — skip Discovery / clarifying-questions / architecture** (devforge already designed + got human approval); may dispatch `devforge-code-explorer` / `devforge-code-architect` for grounding. Output: edit source; write `iter-N/claim.md` (what done / what skipped + specific reason / evidence). Rule: never edit or delete tests.

- [ ] **Step 2: `devforge-review-staff`** — Inputs: `task.md`, `design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` (NOT `claim.md`). Engine: follow `_vendored/staff-review/SKILL.md` against the diff. Output: `iter-N/review-staff-review.md`, first line `VERDICT: PASS|FAIL`, severity-tagged findings (blocker/major/minor/nit).

- [ ] **Step 3: `devforge-review-thermo`** — Inputs: same as staff (NOT `claim.md`). Engine: follow `_vendored/thermonuclear/SKILL.md` (instruction text — not Skill-invoked) against the diff; apply its 1k-line ceiling, spaghetti, code-judo standards. Output: `iter-N/review-thermonuclear.md`, same `VERDICT:`/severity format; map its presumptive-blockers → blocker/major.

- [ ] **Step 4: `devforge-review-code`** — Inputs: `diff.patch` + working tree (NOT a PR, NOT `claim.md`). Engine: follow `_vendored/code-review/code-review.md` multi-agent + confidence-score method **retargeted**: replace `gh pr diff` with reading `iter-N/diff.patch`; drop PR-eligibility (steps 1,7) and the `gh pr comment` step. Output: write findings (score ≥80) to `iter-N/final-review-code-review.md`, first line `VERDICT: PASS|FAIL`.

- [ ] **Step 5: `devforge-validate-brainstorm`** — Inputs: the `<task>`/issue. Engine: follow `_vendored/brainstorming/SKILL.md` clarifying-question discipline **but strip its spec-doc write/commit and its own approval gate** (the orchestrator owns the gate). Still run devforge's GitHub-issue staleness/claim-ledger check. Output: `task.md` + `validation.md`.

- [ ] **Step 6: `devforge-architect-plans`** — Inputs: `task.md`, `validation.md`, codebase. Engine: follow `_vendored/writing-plans/SKILL.md` planning discipline **stripped of its own file-layout/gate steps**. Output: `design.md` in devforge format (approach, files to change, test strategy/oracle, risks).

- [ ] **Step 7: Write `tests/test_adapters.py`**

``python
from pathlib import Path
from conftest import REPO_ROOT

SKILLS = REPO_ROOT / ".claude/skills"

# use value -> adapter dir
ADAPTER = {
    "brainstorming": "devforge-validate-brainstorm",
    "writing-plans": "devforge-architect-plans",
    "feature-dev":   "devforge-impl-feature-dev",
    "staff-review":  "devforge-review-staff",
    "thermonuclear": "devforge-review-thermo",
    "code-review":   "devforge-review-code",
}


def test_every_filler_has_an_adapter_skill():
    for name, d in ADAPTER.items():
        assert (SKILLS / d / "SKILL.md").is_file(), f"missing adapter for {name}"


def test_adapter_references_its_vendored_engine():
    for d in ADAPTER.values():
        text = (SKILLS / d / "SKILL.md").read_text()
        assert "_vendored/" in text, f"{d} does not reference a vendored engine"
``

- [ ] **Step 8: Run the test — verify pass**

Run: `cd tests && python -m pytest test_adapters.py -v`
Expected: 2 passed.

- [ ] **Step 9: Commit**

``bash
git add .claude/skills/devforge-* tests/test_adapters.py
git commit -m "feat(adapters): six slot adapters wrapping vendored engines"
``

---

### Task 5: Orchestrator rewrite — config-driven dispatch + multi-reviewer loop + plan-mode front-end

**Files:**
- Modify: `.claude/skills/devforge/SKILL.md`
- Create: `tests/test_orchestrator_contract.py`

**Interfaces:**
- Consumes: `.devforge/config.json`, `.devforge/registry.json`, the adapter naming map (Task 4), `validate_config.py` rules (followed in prose).

- [ ] **Step 1: Setup phase — load + validate config**

In `### 0. Setup or resume`, add: on fresh start, if `.devforge/config.json` is absent, write the default (Task 1 content) so it's visible/editable; shallow-merge `.devforge/config.local.json` over it if present. Validate every use value against `.devforge/registry.json` (the rules in `scripts/validate_config.py`): unknown use value, use value-not-allowed-in-slot, or duplicate-in-list → STOP with the exact error and the allowed list. Record the resolved config in `progress.md`.

- [ ] **Step 2: Replace skeleton phase steps with slot dispatch**

For `validate`, `architect`, `implementer`: "dispatch a subagent on `slots.<slot>.model` and have it follow `.claude/skills/<adapter-for-use value>/SKILL.md`" (resolve via the naming map; `builtin` = keep the current inline step). Source the adapter only — the subagent does not read `claim.md` for reviewers.

- [ ] **Step 3: Rewrite the inner loop for the `reviewers` list**

After implement + oracle + `diff.patch`: dispatch **one subagent per entry in `reviewers`**, in parallel, each on its model, each following its adapter, each blind to `claim.md` and to the others, each writing `iter-N/review-<use>.md`. Convergence = oracle green AND every finding across **all** `review-*.md` resolved (fixed or specifically justified, nits included). On disagreement between reviewers, the orchestrator records the reconciliation in the next `claim.md`. Escalate after `limits.inner_iterations`.

- [ ] **Step 4: Add the final-review stage**

After inner-loop convergence: if `final_reviewers` is non-empty, dispatch one subagent per entry (parallel, same independence) → `iter-N/final-review-<use>.md`. Any actionable finding reopens the inner loop (a fresh implement→oracle→reviewers iteration), after which the final reviewers re-run; bounded by `limits.final_review_rounds`, then escalate. Empty list → skip straight to the pre-merge gate.

- [ ] **Step 5: Add the plan-mode front-end for the design gate**

In `### 4. DESIGN GATE`: if `plan_mode_gate` is true AND running interactively (not web/headless), present `design.md` via `ExitPlanMode`; on approval, write `.devforge/design.approved` and continue. Otherwise (false, or web/resume) fall back to instructing the human to run `/devforge-approve-design`. The marker file remains the source of truth either way.

- [ ] **Step 6: Update the file-contract table + rules**

In the SKILL.md file-contract table: replace the single `iter-N/review.md` row with `iter-N/review-<use>.md` (per per-iteration reviewer) and add `iter-N/final-review-<use>.md` (per final reviewer); both committed. Update the Rules section to say "resolve every finding across all reviewers."

- [ ] **Step 7: Update `.gitignore` if needed**

`final-review-*.md` are durable → committed (no change). Confirm only `iter-*/diff.patch` and `iter-*/test-results.txt` stay ignored.

- [ ] **Step 8: Write `tests/test_orchestrator_contract.py`**

``python
from conftest import REPO_ROOT

ORCH = (REPO_ROOT / ".claude/skills/devforge/SKILL.md").read_text()


def test_orchestrator_reads_config():
    assert "config.json" in ORCH and "registry.json" in ORCH


def test_orchestrator_documents_per_reviewer_files():
    assert "review-<use>.md" in ORCH
    assert "final-review-<use>.md" in ORCH


def test_orchestrator_has_plan_mode_gate():
    assert "ExitPlanMode" in ORCH and "plan_mode_gate" in ORCH


def test_orchestrator_keeps_marker_gates():
    assert "design.approved" in ORCH and "merge.approved" in ORCH
``

- [ ] **Step 9: Run the full suite**

Run: `cd tests && python -m pytest -v`
Expected: all tests pass.

- [ ] **Step 10: Commit**

``bash
git add .claude/skills/devforge/SKILL.md tests/test_orchestrator_contract.py .gitignore
git commit -m "feat(orchestrator): config-driven slot dispatch, parallel multi-reviewer loop, plan-mode design gate"
``

---

### Task 6: Configuration catalog + README

**Files:**
- Create: `docs/devforge-config.md`
- Modify: `README.md` (the "Status" / "Planned — enrichment" section)

**Interfaces:**
- Consumes: registry + default config + adapter set (final names) from Tasks 1–5.

- [ ] **Step 1: Write `docs/devforge-config.md`**

Sections: (1) *What a slot is* — role = files read/written; use value = config; oracle is not a slot. (2) *Per-slot table* — for `validate`/`architect`/`implementer`/`reviewers`/`final_reviewers`: reads, writes, allowed use values, one-line use value descriptions, recommended model. (3) *Example configs* — paste-ready JSON for `default`, `fast-cheap` (`reviewers:[staff-review]`, empty `final_reviewers`, `inner_iterations:2`, smaller models), `max-rigor` (`reviewers:[staff-review,thermonuclear,code-review]`, opus, `final_review_rounds:3`), `builtin-only` (every slot `builtin`, empty final). (4) *Overrides* — `config.local.json` shallow-merge + validation/error behavior.

- [ ] **Step 2: Validate the catalog's example configs in tests**

Append to `tests/test_config_schema.py`: extract fenced ``json blocks from `docs/devforge-config.md`, validate each against the schema AND `validate_config.validate(...) == []` (except `builtin-only` whose final list is empty — still valid). This keeps the docs honest.

``python
import re, json
from conftest import REPO_ROOT

def test_catalog_examples_are_valid():
    import sys; sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from validate_config import validate
    schema = load_json(REPO_ROOT / ".devforge/config.schema.json")
    registry = load_json(REPO_ROOT / ".devforge/registry.json")
    md = (REPO_ROOT / "docs/devforge-config.md").read_text()
    blocks = re.findall(r"``json\n(.*?)``", md, re.S)
    cfgs = [json.loads(b) for b in blocks if '"slots"' in b]
    assert cfgs, "no example configs found in catalog"
    for c in cfgs:
        jsonschema.validate(c, schema)
        assert validate(c, registry) == []
``

- [ ] **Step 3: Update `README.md`**

Move the relevant "Planned — enrichment" bullets to "Built", and add a "Configuration" subsection pointing to `docs/devforge-config.md` and showing the default `config.json`. Update the file-contract table's `review.md` row to the per-use value naming.

- [ ] **Step 4: Run the suite + commit**

``bash
cd tests && python -m pytest -v
cd .. && git add docs/devforge-config.md README.md tests/test_config_schema.py
git commit -m "docs: configuration catalog + README status update"
``

---

### Task 7: Dogfood end-to-end

**Files:** none committed beyond a `.devforge/` run (per the contract).

- [ ] **Step 1: Run a tiny task with the default config**

Invoke `/devforge "add a CONTRIBUTING.md note about running tests/"` (or similar trivial change). Confirm: config loads + validates; validate/architect produce `task.md`/`validation.md`/`design.md`; the DESIGN GATE fires (plan-mode in CLI); after approval, the inner loop dispatches feature-dev + runs staff-review **and** thermonuclear in parallel, each producing `iter-1/review-<use>.md`; convergence requires all findings resolved; the final stage produces `iter-N/final-review-code-review.md`; PRE-MERGE GATE fires.

- [ ] **Step 2: Run with `builtin-only`**

Set `.devforge/config.local.json` to all-`builtin` / empty final list; confirm the loop still runs end-to-end with zero vendored engines (proves the no-install fallback).

- [ ] **Step 3: Record findings**

Note any adapter/orchestrator wording that confused dispatch; fix inline; re-run the affected stage. Append outcome to `progress.md`.

---

## Self-Review

**Spec coverage:** §3 config + registry → Tasks 1–2; §4 loop control (parallel reviewers, convergence, final-review reopen, plan-mode) → Task 5; §5 vendoring + adapters + VENDORED.md → Tasks 3–4; §6 catalog → Task 6; §8 testing (config validation, vendoring integrity, no-install guard, dogfood) → Tasks 1,2,3,7; the zero-plugin hard rule → Task 3 guard. Covered.

**Placeholder scan:** test code and JSON are complete; markdown-artifact tasks specify frontmatter + the exact Inputs/Engine/Output content and the verbatim scoping rules — no "TBD"/"handle edge cases".

**Type consistency:** `validate(config, registry) -> list[str]` used identically in Tasks 2 and 6; use value→adapter and use value→engine maps match across Tasks 3/4/5; per-reviewer file naming `review-<use>.md` / `final-review-<use>.md` consistent across spec §4/§5 and Tasks 4/5/6.

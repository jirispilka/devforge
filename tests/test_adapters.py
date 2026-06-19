from conftest import REPO_ROOT, load_json

SKILLS = REPO_ROOT / ".claude/skills"

# slot-value name -> adapter dir
ADAPTER = {
    "brainstorming": "devforge-validate-brainstorm",
    "writing-plans": "devforge-architect-plans",
    "feature-dev":   "devforge-impl-feature-dev",
    "staff-review":  "devforge-review-staff",
    "thermonuclear": "devforge-review-thermo",
    "code-review":   "devforge-review-code",
}


def test_adapter_map_covers_every_non_builtin_name():
    registry = load_json(REPO_ROOT / ".devforge/registry.json")
    used = {n for names in registry.values() for n in names} - {"builtin"}
    assert used == set(ADAPTER), f"adapter map out of sync with registry: {used ^ set(ADAPTER)}"


def test_every_name_has_an_adapter_skill():
    for name, d in ADAPTER.items():
        assert (SKILLS / d / "SKILL.md").is_file(), f"missing adapter for {name}"


def test_adapter_references_its_vendored_engine():
    for d in ADAPTER.values():
        text = (SKILLS / d / "SKILL.md").read_text()
        assert "_vendored/" in text, f"{d} does not reference a vendored engine"

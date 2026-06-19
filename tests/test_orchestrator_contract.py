from conftest import REPO_ROOT

ORCH = (REPO_ROOT / ".claude/skills/devforge/SKILL.md").read_text()


def test_orchestrator_reads_config_and_registry():
    assert "config.json" in ORCH
    assert "registry.json" in ORCH


def test_orchestrator_documents_per_reviewer_files():
    assert "review-<use>.md" in ORCH
    assert "final-review-<use>.md" in ORCH


def test_orchestrator_has_plan_mode_gate():
    assert "ExitPlanMode" in ORCH
    assert "plan_mode_gate" in ORCH


def test_orchestrator_keeps_marker_gates():
    assert "design.approved" in ORCH
    assert "merge.approved" in ORCH


def test_orchestrator_dispatches_reviewers_in_parallel():
    assert "parallel" in ORCH.lower()
    assert "final_reviewers" in ORCH


def test_orchestrator_has_dispatch_map_for_every_adapter():
    for adapter in (
        "devforge-validate-brainstorm",
        "devforge-architect-plans",
        "devforge-impl-feature-dev",
        "devforge-review-staff",
        "devforge-review-thermo",
        "devforge-review-code",
    ):
        assert adapter in ORCH, f"orchestrator missing dispatch entry for {adapter}"

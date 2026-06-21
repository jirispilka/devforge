from conftest import REPO_ROOT

ORCH = (REPO_ROOT / ".claude/skills/devforge/SKILL.md").read_text()
APPROVE_DESIGN = (
    REPO_ROOT / ".claude/skills/devforge-approve-design/SKILL.md"
).read_text()


def test_orchestrator_reads_config_and_registry():
    assert "config.json" in ORCH
    assert "registry.json" in ORCH


def test_orchestrator_skill_stays_compact():
    assert len(ORCH.splitlines()) <= 250


def test_orchestrator_documents_per_reviewer_files():
    assert "review-<use>.md" in ORCH
    assert "final-review-<use>.md" in ORCH


def test_orchestrator_has_plan_mode_gate():
    assert "ExitPlanMode" in ORCH
    assert "plan_mode_gate" in ORCH


def test_orchestrator_keeps_marker_gates():
    assert "triage.approved" in ORCH
    assert "design.approved" in ORCH
    assert "merge.approved" in ORCH


def test_orchestrator_has_triage_phase_before_design():
    # Triage is the cheap product-decision step that gates deep analysis/design.
    assert "triage.md" in ORCH
    assert "PROCEED | DEFER | DECLINE" in ORCH
    # Triage must come before validate/architect in the procedure text.
    assert ORCH.index("### 1. Triage") < ORCH.index("### 3. Validate")
    assert ORCH.index("### 2. TRIAGE GATE") < ORCH.index("### 5. Architect")


def test_orchestrator_persists_raw_request_before_triage():
    assert "request.md" in ORCH
    assert "Write it verbatim to" in ORCH
    assert ORCH.index("request.md") < ORCH.index("### 1. Triage")
    assert "`validate` | `request.md`, `triage.md`" in ORCH


def test_orchestrator_selects_review_panel_at_design_gate():
    # Configured reviewer lists are a roster; the design gate picks the per-run panel.
    assert "state.panel" in ORCH
    assert "panel.json" in ORCH
    assert "subset of the configured roster" in ORCH


def test_approve_design_records_the_approved_panel():
    assert "panel.json" in APPROVE_DESIGN
    assert 'state["panel"] = panel' in APPROVE_DESIGN
    assert 'state["phase"] = "inner-loop"' in APPROVE_DESIGN
    assert 'state["iteration"] = 1' in APPROVE_DESIGN


def test_orchestrator_tracks_resumable_post_design_phases():
    for phase in ("inner-loop", "final-review", "final-reopen", "pre-merge-gate"):
        assert phase in ORCH
    assert 'state.phase="pre-merge-gate"' in ORCH


def test_implementer_reads_validated_spec_not_only_design():
    assert (
        "| `implementer` | `task.md`, `validation.md`, `design.md`"
        in ORCH
    )


def test_orchestrator_has_complexity_rubric_with_numbers():
    # Tiers must carry concrete size/blast-radius criteria for consistent rating.
    assert "Complexity rubric" in ORCH
    assert "Blast-radius override" in ORCH
    for tier in ("trivial", "small", "medium", "large"):
        assert tier in ORCH


def test_orchestrator_reopen_reruns_only_final_reviewers():
    assert "re-runs ONLY the final" in ORCH


def test_orchestrator_dispatches_reviewers_in_parallel():
    assert "parallel" in ORCH.lower()
    assert "final_reviewers" in ORCH


def test_orchestrator_uses_universal_dispatch_not_wrapper_skills():
    # The simplification: one contract driven by the registry, no wrapper skill per engine.
    assert "Stage dispatch" in ORCH
    assert "registry.stage_roles" in ORCH and "registry.uses" in ORCH
    assert "separate wrapper skill" in ORCH


def test_orchestrator_resolves_base_plus_repo_registry():
    assert "registry.base.json" in ORCH
    assert "fully-resolved registry" in ORCH
    # repo deltas are still the .devforge/registry.json the existing test checks for
    assert ".devforge/registry.json" in ORCH


def test_no_wrapper_skill_dirs_remain():
    skills = REPO_ROOT / ".claude/skills"
    leftover = [p.name for p in skills.glob("devforge-review-*")]
    leftover += [p.name for p in skills.glob("devforge-impl-*")]
    leftover += [p.name for p in skills.glob("devforge-validate-*")]
    leftover += [p.name for p in skills.glob("devforge-architect-*")]
    assert leftover == [], f"wrapper skill dirs should be gone: {leftover}"


def test_orchestrator_documents_oracle_commands():
    assert "oracle.commands" in ORCH
    assert "inferred fallback" in ORCH
    assert "non-mutating commands" in ORCH
    assert "lint:fix" in ORCH


def test_orchestrator_documents_dirty_worktree_protection():
    assert "git status --porcelain" in ORCH
    assert "pre-existing unrelated changes" in ORCH


def test_orchestrator_finish_step_is_specific():
    assert "Commit with a concise message derived from `task.md`" in ORCH
    assert "PR URL" in ORCH

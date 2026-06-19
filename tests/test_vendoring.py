import subprocess

from conftest import REPO_ROOT, load_json

REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
VENDOR = REPO_ROOT / ".claude/skills/_vendored"

# filler name -> vendored engine path that must exist
ENGINE = {
    "feature-dev":   VENDOR / "feature-dev/feature-dev.md",
    "staff-review":  VENDOR / "staff-review/ENGINE.md",
    "thermonuclear": VENDOR / "thermonuclear/ENGINE.md",
    "code-review":   VENDOR / "code-review/code-review.md",
    "brainstorming": VENDOR / "brainstorming/ENGINE.md",
    "writing-plans": VENDOR / "writing-plans/ENGINE.md",
}


def test_every_non_builtin_filler_has_a_vendored_engine():
    used = {f for fillers in REGISTRY.values() for f in fillers} - {"builtin"}
    for name in used:
        assert ENGINE[name].is_file(), f"missing vendored engine for {name}"


def test_vendored_md_has_entry_per_engine():
    text = (REPO_ROOT / "VENDORED.md").read_text()
    for name in ENGINE:
        assert name in text, f"VENDORED.md missing entry for {name}"


def test_no_committed_skill_references_a_plugin_path():
    # No-install guard: committed skills/agents/config must not point at plugin caches.
    out = subprocess.run(
        ["git", "grep", "-nI", "--cached", "-e", "plugins/cache", "-e", ".claude/plugins",
         "--", ".claude/", ".devforge/"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.stdout == "", f"plugin-path references found:\n{out.stdout}"


def test_vendored_files_are_git_tracked():
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(VENDOR / "staff-review/ENGINE.md")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.returncode == 0, "vendored files must be committed, not gitignored"

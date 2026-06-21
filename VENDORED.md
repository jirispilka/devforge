# Vendored engines

devforge vendors stage engines under `.claude/skills/_vendored/` so a fresh clone or
claude.ai/code attachment works without installing other plugins. Engine files are kept
unmodified; devforge behavior is supplied by `registry.base.json` scopes.

Vendored skills use `ENGINE.md` instead of `SKILL.md` so Claude Code does not auto-register
them as commands. `feature-dev.md` and `code-review.md` keep their upstream filenames.

| `use` | Path | Upstream | Devforge adaptation |
|---|---|---|---|
| `brainstorming` | `_vendored/brainstorming/ENGINE.md` | superpowers 6.0.3 | validate only; writes `task.md` + `validation.md` |
| `writing-plans` | `_vendored/writing-plans/ENGINE.md` | superpowers 6.0.3 | writes short `design.md`; devforge owns gates |
| `feature-dev` | `_vendored/feature-dev/feature-dev.md` | claude-plugins-official | implement-only against approved devforge files |
| `staff-review` | `_vendored/staff-review/ENGINE.md` | apify/agent-skills-internal 1.1.1 | reviews `diff.patch`, blind to `claim.md` |
| `thermonuclear` | `_vendored/thermonuclear/ENGINE.md` | local personal skill | used as instruction text for maintainability review |
| `code-review` | `_vendored/code-review/code-review.md` | claude-plugins-official | retargeted from PR diff to devforge diff/working tree |

Support files from `feature-dev` are also vendored. Two agents are re-registered as project
agents with renamed `name:` fields:

- `.claude/agents/devforge-code-explorer.md`
- `.claude/agents/devforge-code-architect.md`

## Re-sync

1. Re-copy upstream files into `_vendored/`.
2. Re-apply renamed project-agent `name:` values.
3. Update the table if versions or scopes changed.
4. Run `pytest -q`.

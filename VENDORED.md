# Vendored engines

devforge vendors its stage engines under `.claude/skills/_vendored/` so a fresh clone,
plugin install, or claude.ai/code attachment works without installing additional
plugins.

The vendored files are treated as upstream instruction text. devforge-specific behavior
lives in `.claude/skills/devforge/registry.base.json`, where each `use` entry supplies a
scope for the engine.

Most vendored skills are named `ENGINE.md` instead of `SKILL.md` so Claude Code does not
auto-register them as slash commands. `feature-dev.md` and `code-review.md` keep their
upstream filenames because their directories are already nested under `_vendored/`.

| `use` | Path | Upstream | Devforge adaptation |
|---|---|---|---|
| `brainstorming` | `_vendored/brainstorming/ENGINE.md` | superpowers 6.0.3 | validates the request; writes task and evidence files; devforge owns approval gates |
| `writing-plans` | `_vendored/writing-plans/ENGINE.md` | superpowers 6.0.3 | writes the short design; devforge owns execution and gates |
| `feature-dev` | `_vendored/feature-dev/feature-dev.md` | claude-plugins-official | implements against approved devforge files |
| `staff-review` | `_vendored/staff-review/ENGINE.md` | apify/agent-skills-internal 1.1.1 | reviews `diff.patch`, blind to `claim.md` |
| `thermonuclear` | `_vendored/thermonuclear/ENGINE.md` | local personal skill | runs a strict maintainability review |
| `code-review` | `_vendored/code-review/code-review.md` | claude-plugins-official | reviews the devforge diff/working tree instead of a PR diff |

Support files from `feature-dev` are also vendored. Two agents are re-registered as
project agents with devforge-specific `name:` fields:

- `.claude/agents/devforge-code-explorer.md`
- `.claude/agents/devforge-code-architect.md`

## Re-sync

1. Re-copy upstream files into `_vendored/`.
2. Re-apply renamed project-agent `name:` values.
3. Update the table if versions, paths, or scopes changed.
4. Run `pytest -q`.

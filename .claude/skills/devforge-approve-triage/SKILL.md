---
name: devforge-approve-triage
description: HUMAN-ONLY triage-gate approval for devforge. Run after reviewing .devforge/triage.md; writes .devforge/triage.approved and hands back to /devforge. The agent cannot invoke this.
disable-model-invocation: true
allowed-tools: Read, Bash, Skill
argument-hint: ""
---

# Approve triage

Record a human go/no-go so `/devforge` may run validation and design.

1. Read `.devforge/triage.md`; stop if missing.
2. Summarize the problem, decision, complexity, and approach in 3-5 lines.
3. If the decision is `DEFER` or `DECLINE`, warn the user and confirm they still want to
   proceed.
4. Write the marker:
   ```bash
   mkdir -p .devforge
   printf 'approved_at=%s\napproved_commit=%s\nnote=triage approved by human via /devforge-approve-triage\n' \
     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git rev-parse HEAD 2>/dev/null || echo none)" \
     > .devforge/triage.approved
   ```
5. Confirm briefly, then invoke `/devforge` so it resumes from `state.json`.

Do not edit source or analyze code here.

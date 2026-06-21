---
name: devforge-approve-triage
description: HUMAN-ONLY triage-gate approval for the devforge loop. Run this after reviewing .devforge/triage.md to unlock the deep validate + design work — it writes .devforge/triage.approved, which the /devforge loop requires before it will run the validate slot or the architect. The agent cannot invoke this; only a human can approve.
disable-model-invocation: true
allowed-tools: Read, Bash, Skill
argument-hint: ""
---

# Approve triage (human-only gate)

You are recording a **human's** go/no-go on the triage so deep analysis and design can begin.
This is the only thing that opens the triage gate; the agent cannot reach it.

1. Read `.devforge/triage.md`. If it does not exist, STOP and tell the user there is no
   triage to approve yet.
2. Give the user a 3–5 line summary of what they are approving: the problem, the
   **decision** (PROCEED / DEFER / DECLINE), the **complexity** estimate, and the
   high-level approach sketch — so the approval is informed.
3. If the triage decision is `DEFER` or `DECLINE`, **warn the user explicitly** that the
   triage recommended not proceeding, and confirm they still want to approve continuing
   before writing the marker.
4. Write the approval marker so the /devforge loop will proceed to validate + design:
   ```bash
   mkdir -p .devforge
   printf 'approved_at=%s\napproved_commit=%s\nnote=triage approved by human via /devforge-approve-triage\n' \
     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git rev-parse HEAD 2>/dev/null || echo none)" \
     > .devforge/triage.approved
   ```
5. Briefly confirm the approval is recorded, then **continue automatically**: invoke the
   `devforge` skill (`/devforge`). It resumes from `.devforge/state.json` straight into the
   validate step — do not stop to ask the user to re-run anything.

Do NOT edit source files or run analysis *in this skill*. You only record approval and then
hand off to `devforge`, which does the validate + design work under its own context.

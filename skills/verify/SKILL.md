---
name: verify
description: Run ICM stage 03 - report the implementation against the plan's Validation checklist
disable-model-invocation: true
---

# ICM stage 03 - verification

The argument names the plan slug. If it is empty, use the single `status: in-progress` plan in
`plans/`; if that is ambiguous, ask which slug to run.

1. Read `ICM/process-plan/stages/03-verification/CONTEXT.md`. If it is missing, stop and
   suggest `/icm:init`.
2. Execute the stage contract exactly as written, reporting against the Validation checklist in
   `plans/<slug>.md` and the specs its `specs:` frontmatter names.
3. Stop at the workspace's review gate: present the verification report for explicit user
   acceptance. `/icm:document` is the next step once accepted; a spec divergence finding
   re-enters at stage 01 instead.

$ARGUMENTS

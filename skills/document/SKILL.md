---
name: document
description: Run ICM stage 04 - changelog entry, plan closeout and documentation report
disable-model-invocation: true
---

# ICM stage 04 - documentation

The argument names the plan slug. If it is empty, use the single `status: in-progress` plan in
`plans/`; if that is ambiguous, ask which slug to run.

1. Read `ICM/process-plan/stages/04-documentation/CONTEXT.md`. If it is missing, stop and
   suggest `/icm:init`.
2. Execute the stage contract exactly as written - the closeout steps live in
   `plans/README.md`, and only Validation boxes evidenced by the stage 03 report get ticked.
3. Present the closeout for explicit user acceptance. The run ends here; the frozen plan is the
   durable record.

$ARGUMENTS

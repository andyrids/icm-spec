---
name: implement
description: Run ICM stage 02 - bring code into conformance with the accepted techspec
disable-model-invocation: true
---

# ICM stage 02 - implementation

The argument names the plan slug. If it is empty, use the single `status: in-progress` or
`status: planned` plan in `plans/`; if that is ambiguous, ask which slug to run.

1. Read `ICM/process-plan/stages/02-implementation/CONTEXT.md`. If it is missing, stop and
   suggest `/icm:init`.
2. Execute the stage contract exactly as written, working from
   `ICM/process-plan/stages/01-specification/output/<slug>-spec.md` and the plan's Approach.
3. Stop at the workspace's review gate: present the implementation report for explicit user
   acceptance. `/icm:verify` is the next step once accepted.

$ARGUMENTS

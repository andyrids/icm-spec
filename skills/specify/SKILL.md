---
name: specify
description: Run ICM stage 01 - turn a feature request into a spec change, a plan and a techspec
disable-model-invocation: true
---

# ICM stage 01 - specification

The argument is the feature request. If it is empty, ask for one before doing anything else.

1. Read `CONTEXT.md` at the repository root, then `ICM/process-plan/CONTEXT.md`, then
   `ICM/process-plan/stages/01-specification/CONTEXT.md`. If any of these is missing, stop and
   suggest `/icm:init`.
2. Execute the stage contract exactly as written - it defines the inputs, process and outputs.
3. Stop at the workspace's review gate: present the spec change, the plan and the techspec for
   explicit user acceptance before any implementation begins. `/icm:implement` is the next step
   once accepted.

$ARGUMENTS

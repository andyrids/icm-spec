---
name: express
description: >
   Run the ICM express-change pipeline - a small change no spec has to move for, with the plan
   record left intact
disable-model-invocation: true
---

# ICM express-change

The argument is the change request. If it is empty, ask for one before doing anything else.

1. Read `CONTEXT.md` at the repository root, then `ICM/express-change/CONTEXT.md`, then
   `ICM/express-change/stages/01-change/CONTEXT.md`. If any of these is missing, stop and suggest
   `/icm:init`.
2. Test eligibility before writing anything, and state the verdict with its reason in the visible
   response. If the work needs a `specs/**` change, stop and hand off to `/icm:specify`. Do not
   amend a spec here - that is the one thing this pipeline exists not to do.
3. Execute the stage contract exactly as written - it defines the inputs, process and outputs.
4. Stop at the single review gate: present the plan, the diff and the test result for explicit
   user acceptance. The run ends there; the frozen plan is the durable record.

$ARGUMENTS

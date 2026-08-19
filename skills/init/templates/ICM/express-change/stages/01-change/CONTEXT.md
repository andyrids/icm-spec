---
context-hierarchy: Layer 2
context-hierarchy-role: Stage contract
immutable: false
recommended-context-tokens: 500
---

# Stage 01 - change

Make a small change that no spec has to move for, and leave the same durable record the
four-stage pipeline leaves.

## Inputs

- The change request, as given by the user
- `specs/**` - read to establish that no spec has to change, which is the eligibility test
- `plans/README.md` - the frontmatter contract, section order and closeout steps
- `ICM/_config/reference-standard-validation.md` - EARS patterns for the Validation checklist
- `ICM/_config/reference-standard-yagni.md` - the scope boundary
- `ICM/_config/reference-toolchain-*.md` - loaded per tool, only as each tool comes into play

## Process

1. Test eligibility against `../../CONTEXT.md` and state the verdict with its reason in the
   visible response. If any condition fails, stop and route to `/icm:specify`.
2. Open `plans/<slug>.md` at `status: in-progress`, per `plans/README.md`. `specs:` names the
   specs the change conforms to; `authors:` stays empty, because a populated `authors:` means a
   spec moved and express never applied.
3. Make the change, staying inside the plan's Scope. Scope that grows mid-run is the signal the
   eligibility call was wrong - stop and re-enter `process-plan` rather than widening it here.
4. Run the project's test and coverage commands as the toolchain references define them, capture
   the result verbatim, and report each Validation criterion against it.
5. Close the plan out per `plans/README.md` - a ticked box appends its evidence citation - and
   add the `CHANGELOG.md` entry.

## Outputs

- Source and test changes
- A `CHANGELOG.md` entry
- `plans/<slug>.md` frozen at `status: done`

This stage writes no `output/` artifact. The plan is the edit surface, and unlike stage scratch it
is tracked.

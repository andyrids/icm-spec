---
context-hierarchy: Layer 2
context-hierarchy-role: Stage contract
immutable: false
maximum-context-tokens: 500
---

# Stage 04 - documentation

Close the run out: the changelog gains an entry, the plan freezes as the durable record, and
nothing this run produced is left implicit.

## Inputs

- All three prior stage reports under `../*/output/<slug>-*.md`
- `plans/<slug>.md` and the closeout steps in `plans/README.md`
- `CHANGELOG.md` and `ICM/_config/reference-standard-changelog.md`

## Process

1. Add the `CHANGELOG.md` entry under `[unreleased]`, typed per Keep a Changelog.
2. Close the plan out per `plans/README.md`: flip `status` to `done`, set `pr:`, tick only the
   Validation boxes the stage 03 report evidences, appending each box's evidence citation
   (`ICM/_config/reference-standard-validation.md`) - an unticked box with a reason in Notes
   beats a ticked one that was never checked.
3. Populate Notes (decisions, gotchas, pins) and Follow-ups using the taxonomy; a `Deferred to`
   entry edits the named downstream plan in the same commit.
4. Update any user-facing documentation the feature touches.

## Outputs

- A `CHANGELOG.md` entry
- `plans/<slug>.md` frozen at `status: done`
- `output/<slug>-docs.md` - documentation report: what was recorded where, and any follow-up
  left open

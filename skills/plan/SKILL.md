---
name: plan
description: How to open, work and close plans/<slug>.md files - the motion side of the state/motion split
paths:
  - "plans/**"
---

# Working under plans/

`plans/` is the planning system - one file per unit of work, frozen at `status: done` as the
durable record. The full protocol, frontmatter contract and closeout steps are
`plans/README.md`. Read it before writing.

The rules that bite most often:

- Frontmatter is queried, so it must stay exact: `status` is one of
  `planned | in-progress | done | blocked | cancelled`; `specs:` and `authors:` paths must
  resolve; the Layer 4 hierarchy keys are present.
- The two spec fields answer different questions. `specs:` means this plan brings **code** into
  conformance and stage 03 verifies against it; `authors:` means this plan writes the spec and
  changes no behaviour. One field, never both - over-listing `specs:` silently defeats the
  coverage invariant, which is how it died the first time.
- Body section order is fixed: Scope, Implements, Approach, Validation, Risks / unknowns, Notes,
  Follow-ups. Validation supplies the requirement identifiers stage 03 reports against, and its
  criteria are written in EARS (`ICM/_config/reference-standard-validation.md`).
- At closeout, tick a Validation box only where evidenced; an unticked box with a reason in
  Notes beats a ticked one that was never checked.
- A `Deferred to` follow-up edits the named downstream plan in the same commit, or the work is
  lost between two documents.

Plans are opened by ICM stage 01 (`/icm:specify`) and frozen by stage 04 (`/icm:document`).

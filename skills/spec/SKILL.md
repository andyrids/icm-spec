---
name: spec
description: How to author and change files under specs/ - the state side of the state/motion split
paths:
  - "specs/**"
---

# Working under specs/

`specs/` declares what MUST be true - permanent desired state, changed only by review. The full
protocol is `specs/README.md`; the authoring bar and templates are
`ICM/_config/reference-standard-spec.md`. Read both before writing.

The rules that bite most often:

- Specs state behaviour observable from outside the implementation - invocation, outputs,
  failure modes, errors. Never function names, module paths or test cases; those rot on the
  first refactor.
- Every spec carries `## Out of scope`: the adjacent capability a reader would assume is
  included, and where it went. Edge cases stay in the spec too, as `If <trigger>, then` criteria.
- Behaviour is stated in EARS (`ICM/_config/reference-standard-validation.md`). The prose *about*
  authoring a spec stays in modal form; the requirements inside one do not.
- The level-of-detail test: could two implementers read it and disagree about whether the code
  conforms? If yes, it is too vague.
- A new spec on the default branch needs an owning plan unless the behaviour already exists -
  named in that plan's `specs:` if code changes to conform, its `authors:` if the plan only
  writes the spec. Invariant 1 in `specs/README.md`.
- After amending a spec, run the ripple check: `grep -l '<spec path>' plans/*.md`, then flag the
  plans chasing the old desired state.
- Spec/code divergence is a bug, not debt. Fix the code or amend the spec - never work around a
  spec in code.

Spec authorship belongs to ICM stage 01 (`/icm:specify`). Editing a spec mid-implementation is a
re-entry decision, not a quiet patch.

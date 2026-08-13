---
context-hierarchy: Layer 2
context-hierarchy-role: Stage routing
immutable: false
maximum-context-tokens: 500
---

# Workspace: express-change

One stage. For work that conforms to specs already on the default branch and lands in a single
commit. The four-stage pipeline's cost is in its handoffs, and a change with nothing to hand off
pays that cost for nothing.

The single stage is `stages/01-change/`; its `CONTEXT.md` holds the full contract.

## What is given up, and what is not

Given up: the techspec, the three intermediate reports, and three of the four review gates.
Those carry a decision from one stage to the next, and here there is no next.

Not given up: the plan. It is opened, validated and frozen exactly as `plans/README.md`
prescribes, because the plan is the record and skipping it is what hollows the record out. The
Stop gates still fire, so an unfinished closeout still blocks.

## Eligibility

Express applies only when all three hold:

- No `specs/**` change is required - the work conforms to a spec already on the default branch,
  or touches nothing specs cover (`specs/README.md`).
- It is one commit's worth of work, with no new dependency and no new public surface.
- Every Validation criterion can be evidenced within this run.

The first condition carries the design. Needing a spec change *is* what makes work not small, so
eligibility cannot be used to slip a behaviour change past stage 01.

Work that turns out to need a spec re-enters `process-plan` at stage 01, carrying its plan across
- the plan is already open and already named, and nothing about it needs rewriting.

## Acceptance criteria

- The eligibility verdict MUST be stated with its reason before anything is written, so a wrong
  call is objected to rather than discovered later.
- One unconditional review gate, at the end, over the plan, the diff and the test result.
- User review & acceptance MUST be explicit before the run closes:
  - 'approved' or 'continue' - proceed as presented
  - approval carrying changes - apply them; if they change observable behaviour the work was
    never eligible, and re-enters `process-plan` at stage 01

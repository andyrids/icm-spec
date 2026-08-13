---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: [plans, protocol, closeout]
---

# Plans

`specs/` describes **state** - what should be true, forever. `plans/` describes **motion** - how
we are getting there next.

One file per unit of work, `plans/<slug>.md`, using the same kebab-case slug the ICM stage
artifacts share (`ICM/_config/reference-standard-naming.md`).

Plans are temporal. Once merged they **freeze** as historical record: the merged PR link plus the
completed validation checklist is the project's working memory of what got built, how, and what
was deferred.

## This is the planning system

`plans/` is not a substitute for, and is not substituted by, an agent's built-in plan mode. An
ephemeral plan evaporates when the turn ends, leaving no record. If a scratchpad is used to
think, the artifact still lands here.

The classic failure: drafting an ad-hoc plan of 'write spec X, then build it', doing exactly
that, and leaving behind neither a reviewed spec change nor a plan file. Split it - the spec
change goes through `specs/`, and the work to execute it gets a file here.

Even small work leaves a plan. Skipping it because a change is 'quick' is what hollows the record
out.

That is why the fast path is a shorter *pipeline*, not a plan-free one. `ICM/express-change/`
drops the techspec and the intermediate reports for work no spec has to move for, and opens,
validates and freezes the plan exactly as this file prescribes. If a change is too small to
deserve a plan, it is too small to have needed a pipeline either.

No DAG drawing or status table is maintained in this file - both rot the moment someone forgets
to update them. Query the frontmatter instead:

```sh
grep -l 'status: planned' plans/*.md            # what could be started
grep -l 'specs/commands/<verb>.md' plans/*.md   # what a spec change ripples into
```

Use a placeholder when documenting these queries - a real spec path written into prose here
makes this file a false positive in every ripple check that greps for it.

**Two different questions, two different queries.** The ripple check above is deliberately broad:
after editing a spec you want every plan that so much as mentions it. The *coverage* check behind
Invariant 1 in `specs/README.md` is the opposite - it must read only the frontmatter `specs:` and
`authors:` blocks, because a plan's prose routinely names specs it does not own, and counting
those as coverage lets the invariant pass on specs nothing owns. Never answer 'is this spec
covered?' with a whole-file grep.

## Frontmatter

```yaml
---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: planned        # planned | in-progress | done | blocked | cancelled
depends: []            # other plan slugs that must land first
specs:                 # specs this plan brings CODE into conformance with
  - specs/commands/<verb>.md
authors: []            # specs this plan WRITES, with no behaviour change
issues: []             # issue numbers
pr:                    # PR number, set at closeout
---
```

### `specs:` means conformance; `authors:` means authorship

The two fields answer different questions, and putting a spec in the wrong one breaks a different
check each way.

- **`specs:`** - this plan changes code until it conforms. Stage 03 verifies observable behaviour
  against every entry here, so a spec listed without matching code produces a false divergence
  finding.
- **`authors:`** - this plan writes or amends the spec and changes no behaviour. Nothing is
  verified against it; the field exists so a spec-authoring plan can own its spec without claiming
  a conformance it never delivers.

A spec belongs in one field, never both. If the same plan writes a spec *and* implements it, that
is `specs:` - the code conformance is the stronger claim and subsumes the authorship.

Invariant 1 in `specs/README.md` accepts either field, so `specs: []` with a populated `authors:`
is a complete answer to 'who owns this spec?'.

This is where the methodology walked into its one real trap on first use: the plan that created
this directory listed every spec file in `specs:`, having authored them. Every spec then had a
covering plan by `grep`, so Invariant 1 could never fail and the drift auditor was silently
useless. The check was built and defeated in the same commit.

`authors:` exists so that the honest answer is also the cheap one. The invariant is only worth
having if a spec can fail it, and over-listing `specs:` is how it quietly stops being able to.

## Body

Fixed section order: **Scope**, **Implements**, **Approach**, **Validation**, **Risks /
unknowns**, **Notes**, **Follow-ups**.

`Implements` is the prose companion to the frontmatter: which specs this plan answers, and which
parts of them. It is written for people. Nothing reads it to decide coverage - the gates read
`specs:` and `authors:` - so a spec named here and in neither field is an uncovered spec with a
paragraph about it.

`Validation` is load-bearing - it is the checkbox list that converts `in-progress` to `done`, and
it supplies the requirement identifiers the ICM verification stage reports against. Its criteria
are written in EARS, per `ICM/_config/reference-standard-validation.md`. `Notes` and `Follow-ups`
stay empty until closeout.

## Status lifecycle

```text
planned -> in-progress -> done      (frozen; edit only to correct the record)
                       -> blocked
                       -> cancelled
```

## Closeout

The last commit before merge:

1. Flip `status` to `done` and add `pr:`.
2. Tick validation boxes **only where verified**, appending each ticked box's evidence citation
   after the em dash separator (`ICM/_config/reference-standard-validation.md`). Leave unverified
   boxes unticked and say why in Notes - a ticked box that was not checked is worse than an
   unticked one.
3. Populate Notes: decisions, gotchas, version pins - and the *why this design* reasoning, which
   otherwise lives only in the techspec and is deleted with the run's scratch. Notes is the one
   durable home design rationale has.
4. Populate Follow-ups using the taxonomy below.
5. Absorb any deferrals (see below).
6. Reconcile `specs/` - if the implementation diverged, fix the code or amend the spec.

## Follow-ups taxonomy

- **Issue `[#N](link)`** - actionable, but owned by no current plan.
- **Deferred to `[<plan>](<plan>.md)`** - work an unstarted downstream plan will absorb.
- **Tracked as** - external dependencies that are neither issue nor plan.
- **None** - state this explicitly. Silence is ambiguous.

## Deferral absorption

A `Deferred to` entry MUST, **in the same commit**, edit the named downstream plan to absorb it -
typically a bullet in its Approach plus a new Validation criterion, cross-linked back.

Without this the deferral is a non-binding pointer the downstream plan can ignore, and the work
is silently lost between two documents that each assume the other owns it.

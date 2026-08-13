---
context-hierarchy: Layer 2
context-hierarchy-role: Stage contract
immutable: false
maximum-context-tokens: 500
---

# Stage 01 - specification

Turn a feature request into three artifacts: a spec change, a plan, and a techspec. Nothing is
implemented here - this stage decides what will be true and how the work is shaped.

## Inputs

- The feature request, as given by the user
- `specs/**` - the current declared state, and where the change lands
- `specs/README.md` and `plans/README.md` - the tree invariants and the plan protocol
- `ICM/_config/reference-standard-spec.md` - authoring bar and spec templates
- `ICM/_config/reference-standard-validation.md` - EARS patterns for the Validation checklist
- `ICM/_config/reference-standard-techspec.md` - techspec template
- `ICM/_config/reference-standard-naming.md` - the shared `[slug]`

## Process

1. Choose the kebab-case slug; it correlates every artifact this run produces.
2. Write or amend the spec under `specs/**` - declarative, observable behaviour only, per the
   authoring standard. After amending, run the ripple check in `specs/README.md`.
3. Open `plans/<slug>.md` at `status: planned`, using the frontmatter contract and fixed section
   order in `plans/README.md`. A spec goes in `specs:` if this plan changes code to conform, in
   `authors:` if it only writes it - one field, never both. Write Validation criteria in EARS.
4. Draft the techspec from the template into `output/<slug>-spec.md`. Mark any unresolved
   decision inline as `[NEEDS CLARIFICATION: <question>]` rather than guessing an answer.
   Unresolved markers block stage 02.

## Outputs

- A spec change under `specs/**`
- `plans/<slug>.md` at `status: planned`
- `output/<slug>-spec.md` - the techspec, ephemeral scratch

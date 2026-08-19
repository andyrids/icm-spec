---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [techspec, SDD]
---

# Technical spec: [slug]

The techspec is the *how*. It is ephemeral scratch, gitignored, and rebuilt per run.

It does not carry the feature narrative - that belongs in `specs/**`, which is permanent - and it
does not carry the acceptance criteria, which belong in a plan Validation checklist.

It opens with the Layer 4 stage output frontmatter in `reference-standard-naming.md`, then:

## (1) Spec delta

{{Name the `specs/**` files created or amended, and summarise what is now declared true. Link the
plan at `plans/[slug].md`. Do not restate the spec here - point at it.}}

## (2) Component architecture

{{List specific files within the project that require modification or creation. List required
external dependencies.}}

## (3) Interface and UX

{{Detail how the feature meets its interface - terminal, API or tool surface. Specify entry-point
changes, output stream behaviour, logging and formatting, per the conventions in
`reference-toolchain-*.md`.}}

## (4) Implementation directives

{{Provide the step-by-step logic required to fulfill the objective. Detail data mutations and
function flow.}}

## (5) Toolchain and error handling

{{Specify requirements to satisfy the linters and type checkers named in
`reference-toolchain-*.md`. Edge cases live in the spec delta as `If <trigger>, then` criteria -
do not restate them here. Define only the implementation-side error handling: which package
exceptions are raised, and where.}}

## (6) Verification requirements

{{Do not restate acceptance criteria here - the Validation checklist in `plans/[slug].md` is the
single source, and its checkbox text supplies the requirement identifiers 03-verification reports
against. List only the specific functions or classes needing new unit test coverage, each mapped
to the Validation criterion it serves.}}

## (7) References

{{List all project files or external material that were read to generate this specification.}}

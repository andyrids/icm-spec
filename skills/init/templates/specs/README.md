---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: [specs, invariants, protocol]
---

# Specifications

`specs/` declares what MUST be true of the project. It is the source of truth for behaviour.

This is not documentation of what was built - it is specification of what should exist.
Implementation is brought into conformance with these files, not the other way round.

## State vs motion

The project keeps three distinct artifact kinds. Confusing them is the failure mode this tree
exists to prevent.

| Layer    | Answers                      | Location            | Lifetime                     |
| -------- | ---------------------------- | ------------------- | ---------------------------- |
| Spec     | What MUST be true, forever   | `specs/**`          | Permanent, changed by review |
| Plan     | What we are doing about it   | `plans/<slug>.md`   | Frozen at `status: done`     |
| Techspec | How, in implementation terms | ICM stage `output/` | Ephemeral scratch            |

A spec with no implementation is a known gap, and on the default branch a known gap MUST carry a
committed plan. That invariant is what makes the `spec-drift-auditor` agent meaningful - see
[Invariants](#invariants) below.

## Layout

```text
specs/
├── README.md         <- this file
├── principles.md     <- decisive, project-wide rules (create on first promotion)
├── commands/         <- one file per CLI verb, if the project has a CLI
├── behaviors/        <- cross-cutting invariants spanning several commands
└── mcp/              <- MCP tool contracts, if the project serves MCP
```

Subdirectories are created as the project needs them, not up front. The names above are
illustrative - a project without a CLI has no `commands/`, and one that serves no MCP has no
`mcp/`. Group by the shape of the thing being specified, one file per unit.

## What specs cover

Invocation and inputs, data requirements, outputs, failure modes, out of scope, and principles.

## What specs do NOT cover

Module decomposition, function and variable names, file paths inside the implementation, and test
cases. Those are implementation decisions that change freely; a spec that pins them rots on the
first refactor. Authoring guidance and templates are in
`ICM/_config/reference-standard-spec.md`.

## Specification authority

How much authority the spec holds over the code is a chosen position, not a given. Three exist:

- **Spec-first** - the spec is written and reviewed, implementation follows, and the document is
  thereafter history.
- **Spec-anchored** - the spec evolves with the software, and automated tests bridge the two.
- **Spec-as-source** - the spec is the only hand-written artifact; code is regenerated from it.

This tree is **spec-anchored**. That commits the project to three things: the spec is amended
whenever desired behaviour moves, and stage 01 owns every amendment; tests are the bridge, so a
ticked Validation box cites its evidencing test at closeout
(`ICM/_config/reference-standard-validation.md`); and no human refactor is skipped because the
spec changed - Invariant 2 below is this stance stated as a rule, not a house preference.

A project wanting a different position edits this section. The pipeline does not change.

## Invariants

1. Every spec on the default branch is either implemented or owned by a committed plan, named in
   that plan's `specs:` field if the plan brings code into conformance with it, or its `authors:`
   field if the plan only writes it. Coverage is computed from frontmatter, never a whole-file
   grep - `plans/README.md` says why.
2. Spec/code divergence is a bug, not debt. Fix the code, or amend the spec - never work around a
   spec in code. This is the spec-anchored stance above, applied one divergence at a time.
3. A spec whose desired state is still being negotiated stays off the default branch, on a
   feature branch, until its plan rides along with it. Absence is the only unambiguous marker; a
   `draft` field would still pollute greps and reading context.
4. Where the project exposes a CLI, `<cli> <cmd> --help` is authoritative for invocation. If a
   command spec disagrees with it, `--help` wins and the spec needs updating.

## Changing a spec

A spec edit can strand work already planned against the old desired state. After editing, find
the plans chasing it and offer to update them:

```sh
grep -l 'specs/commands/<verb>.md' plans/*.md
```

A `planned` plan may need its scope, approach or validation revised. Flag - do not silently
rewrite - an `in-progress` plan.

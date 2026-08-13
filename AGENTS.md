---
context-hierarchy: Layer 0
context-hierarchy-role: Global identity
immutable: false
maximum-context-tokens: 900
---

# `icm-spec` plugin

This project contains a plugin for implementing spec-driven development alongside Interpretable
Context Methodology (ICM).

ICM orchestrates agent workflows through workspaces with folder structure, markdown and scripts.

Workspaces use dedicated pipelines containing stages with a specific input, process and output.
Conditional and unconditional review gates MUST be respected to allow human inspection and
feedback loops.

## Context hierarchy

Five layers. Layers 0 to 2 route; layers 3 and 4 carry content. Load a layer only when the work
has reached it - reading ahead is how a stage acquires context it was designed not to have.

| Layer | Role              | Path                            | `immutable` | Budget |
| ----- | ----------------- | ------------------------------- | ----------- | ------ |
| 0     | Global identity   | `AGENTS.md`                     | false       | 900    |
| 1     | Workspace routing | `CONTEXT.md`                    | false       | 300    |
| 2     | Stage routing     | `ICM/*/CONTEXT.md`              | false       | 500    |
| 2     | Stage contract    | `ICM/*/stages/**/CONTEXT.md`    | false       | 500    |
| 3     | Reference material| `ICM/_config/reference-*.md`, both READMEs | true | 2500 |
| 3     | Desired state     | `specs/**/*.md`                 | false       | -      |
| 4     | Working artifact  | `plans/*.md`                    | false       | -      |
| 4     | Working artifact  | `ICM/*/stages/**/output/*.md`   | false       | -      |

### Frontmatter

Every file above carries `context-hierarchy`, `context-hierarchy-role` and `immutable` as tabled,
plus `maximum-context-tokens` where a budget is given. Beyond those:

- **Budgets are ceilings, not suggestions.** A file that outgrows one has started doing another
  layer's job. Specs are unbudgeted - a spec is as long as the behaviour it declares.
- **Layer 3** carries `tags: [keyword, ...]`. `immutable: true` marks the factory configuration,
  amended deliberately, not in passing. Specs are not part of it: the pipeline exists to amend
  them, and stage 01 owns every change.
- **`plans/*.md`** carries `status` - `planned | in-progress | done | blocked | cancelled` - plus
  the query fields `depends`, `specs`, `authors`, `issues` and `pr`, contracted in
  `plans/README.md`. Every coverage and ripple check reads them.
- **`ICM/*/stages/**/output/*.md`** carries `status: in-progress | in-review | done`. It is
  ephemeral scratch, gitignored.

## Design principles

1. **One stage, one job** - each workspace stage handles a single step of a workflow.
2. **Plain text as the interface** - stages communicate through plain text.
3. **Layered context loading** - agents only load context relevant for the current stage.
4. **Output is an edit surface** - intermediate stage output can be opened, read, edited & saved.
5. **Configure the factory, not the product** - new deliverables can use the same configuration.

## Stage contracts and handoffs

Each stage in an ICM workspace (`ICM/*`) defines a contract with three parts; what it
reads (inputs), what it does (process) and what it writes (outputs). This contract is provided in
every `ICM/*/stages/**/CONTEXT.md`.

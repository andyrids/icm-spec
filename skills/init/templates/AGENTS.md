---
context-hierarchy: Layer 0
context-hierarchy-role: Global identity
immutable: false
maximum-context-tokens: 900
---

# [Project name]

[Replace this paragraph. State what the project is, who it serves, and the one or two constraints
an agent must never violate. This block is the only project-specific part of the file.]

This project follows Interpretable Context Methodology (ICM): agent workflows orchestrated through
workspaces of folder structure, markdown and scripts, each a pipeline of stages with a defined
input, process and output. Review gates MUST be respected - they are where a human inspects the
work and hands it back.

Start at `CONTEXT.md` in the repository root; it routes to the workspace that owns the work.

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
| 3     | Reference material| `specs/**/*.md`                 | false       | -      |
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

1. **One stage, one job** - each stage handles a single step of a workflow.
2. **Plain text as the interface** - stages communicate through plain text.
3. **Layered context loading** - agents load only what the current stage needs.
4. **Output is an edit surface** - stage output can be opened, read, edited and saved.
5. **Configure the factory, not the product** - new deliverables reuse the same configuration.

## Stage contracts

Each stage defines a contract in three parts - what it reads, what it does, what it writes -
stated in its own `ICM/*/stages/**/CONTEXT.md`, which is the authority for that stage.

A contract cites the rules it depends on rather than restating them. Where a stage and a reference
disagree, the reference wins and the contract is what needs fixing.

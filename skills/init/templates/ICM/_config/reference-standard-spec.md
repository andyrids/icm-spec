---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: [spec, SDD]
---

# Standard - specifications

How to write a file in `specs/`. The tree layout and the invariants it holds are in
`specs/README.md`; this file is the authoring bar and the templates.

## The right level of detail

Specs declare **what** MUST be true, not **how** to implement it.

- **Too vague** - 'The importer handles duplicate records sensibly.' An implementer still has to
  make a hundred decisions. Replace or reject? Reported how? What counts as a duplicate?
- **Right** - 'When a record arrives with a known identifier, the importer shall replace the
  stored copy and report the count of replacements on completion. If a record arrives malformed,
  then the importer shall reject it and continue the batch.' Testable by running one batch.
- **Too detailed** - 'Call `find_record(key)`, compare via `record.fingerprint()`, pass the
  survivor to `store.upsert` with fields `[...]`.' This is writing the code twice, and it rots on
  the first refactor.

The test: could two implementers read it and disagree about whether the code conforms? If yes, it
is too vague to be a spec.

## Requirement notation

Statements about system behaviour are written in EARS - the templates, and the subject test that
decides when they apply, are in `reference-standard-validation.md`. That covers a spec's rules,
its output description and every Validation criterion a plan derives from it.

The rules in the next section are addressed to whoever is authoring the spec rather than to the
system, so they stay in modal form. That split is the whole of the policy: EARS for what the
system does, modals for what a person does.

## Rules

- MUST state behaviour observable from outside the implementation - invocation, outputs, failure
  modes, errors
- MUST NOT name functions, variables or module paths as requirements; those change freely
- Where the project exposes a CLI, MUST NOT restate `--help` output as prose. The `--help` text
  is authoritative; a spec that disagrees with it is the thing that is wrong
- SHOULD explain *why* a non-obvious rule exists, in one line. A rule whose reason is lost gets
  'simplified' away by the next implementer
- SHOULD NOT duplicate a behaviour spec into an interface spec - link to it

## Edge cases

Edge cases are spec content, not implementation scratch. Behaviour at the margins is still
observable behaviour, and an edge case recorded only in a techspec is deleted with the run's
scratch. Enumerate them in the spec - under Failure modes in an interface spec, under Details in
a behavior spec - as EARS unwanted criteria: `If <trigger>, then`. That pattern is the edge-case
enumerator, and a spec with no If clause has probably not looked for its failures.

## Out of scope

Both templates carry an `## Out of scope` section, because the most expensive misreading of a
spec is the adjacent capability a reader would reasonably assume is included - the importer that
surely also validates, the search that surely also paginates. Name each such assumption and say
where it went: a plan Follow-up, a named future spec, or never, with the why.

This is not `specs/README.md`'s 'What specs do NOT cover'. That section rules out *kinds of
statement* - module names, test cases - and applies to every spec identically; Out of scope
rules out *behaviour* this one spec deliberately excludes, and is written fresh each time.

## Principles

A principle is a generative rule that resolves the cases enumeration never reaches. It earns its
place only if it is **decisive**: it picks a side of a real trade-off and rules something out.

- **Not a principle** - 'Output should be clean and agent-friendly.' Rules nothing out.
- **A principle** - 'On single-object payloads, efficiency comes from truncation, not the
  encoding; MUST NOT relax the truncation default to compensate.' An implementer can act on it.

`ICM/_config/reference-standard-yagni.md` is the in-repo worked example - every line picks a
side.

### Placement

Default to **the most specific spec the principle governs**. A principle shaping one interface
belongs in that interface spec's `## Principles` section, next to the rules it backs, where an
implementer reading only that file will see it.

Reserve `specs/principles.md` for genuinely project-wide rules. The trigger to promote is
**the same or a similar principle appearing in a second spec** - that duplication means it has
outgrown any one file. Lift it once, then replace both copies with references, rather than
letting two near-identical statements drift apart.

Do not agonize at capture time. Put it on the spec you are in; promote later if it spreads.

### Referencing back down

Promotion sends principles up; this is the flow back down. An agent working from one interface
spec will not open `specs/principles.md` on its own, so a project-wide principle quietly
governing that interface is invisible.

In a spec's `## Principles` section, name the `specs/principles.md` entries that **especially bite
here**, each with a one-line gloss of how it applies, linked to the full statement. Be selective:
a spec that links every principle teaches nothing.

Use the two-part shape - **Inherited** for linked `specs/principles.md` entries, **Local** for
principles this spec owns. Omit either subsection if empty.

## Templates

### Interface spec

One file per unit of public surface - a CLI verb, an API endpoint, an MCP tool. The H1 keeps the
`Kind: Name` prefix from `reference-standard-markdown.md` - `# Command: <cli> find`,
`# Tool: inspect`. Stack mechanics - exit-code enums, payload encodings, help footers, console
formatting - are toolchain conventions declared once in `reference-toolchain-*.md`; the spec
states what the caller observes, and the toolchain reference names the mechanism carrying it.

```markdown
# Command: <cli> <verb>

## Invocation / inputs
What the unit accepts - arguments, flags, request fields - with defaults, as a table.

## Data requirements
What the unit reads - stored state, configuration, live introspection.

## Outputs
Declarative description of what is emitted: fields present by default, ordering,
truncation, and the definitive empty state with its hint.

## Failure modes
The edge cases, as `If <trigger>, then` criteria: bad input, missing state, denied
access - and what the caller observes for each, including how failure is signalled.

## Out of scope
Adjacent behaviour this spec deliberately excludes, and where each item went.

## Principles (optional)
**Inherited** - `principles.md` entries that bite here, one-line gloss each.
**Local** - principles owned by this unit.
```

### Behavior spec

```markdown
# Behavior: <name>

## Rule
The invariant, stated declaratively.

## Applies to
Which commands, tools or modules this governs.

## Details
Calculations, ordering, and the edge cases as `If <trigger>, then` criteria.

## Out of scope
Adjacent behaviour this spec deliberately excludes, and where each item went.

## Principles (optional)
Same two-part shape as above.
```

### Principle entry

```markdown
## <Short, stable heading>
The rule, stated so it rules something out. Include the *why* - the context
that makes the trade-off land - so a future reader applies it correctly
rather than literally.
```

The heading is the anchor other specs link to (`principles.md#<name>`). Keep it stable; changing
it breaks every inbound reference.

## Watch for specs mid-task

This is standing, not a stage. While implementing, debugging or reviewing, watch for the moment a
decision gets resolved that would change how a *future* implementer decides something:

- The user explains *why* they want something a certain way
- A trade-off is settled in conversation ('always favour X over Y')
- An unspecified case is hit, an answer picked, and that answer implies a general rule
- A 'we'll always' or 'we'll never' sentiment surfaces
- The same principle turns up in a second spec - the loudest promotion signal there is

When noticed, **stop and surface it**: name the decision, say whether it reads as an enumerated
rule or a principle, and propose where it belongs.

The bar: if it would only ever have affected that one line, let it go. If it would change a
future decision, it belongs in a spec.

A decision that lives only in code, a commit message or a chat scrollback is unspecified
behaviour the moment the context window closes - and the next agent will re-litigate it,
possibly differently.

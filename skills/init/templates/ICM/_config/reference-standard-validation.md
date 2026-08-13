---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: [validation, EARS, requirements, SDD]
---

# Standard - validation criteria

The Validation checklist in `plans/[slug].md` is the most load-bearing list in the methodology. It
converts `status: in-progress` to `done`, its checkbox text supplies the requirement identifiers
03-verification reports against, and the closeout gate reads it. This file is its authoring bar.

The same bar governs requirement statements inside `specs/**`. A spec declares what MUST be true
and a Validation criterion asserts that it now is; they are the same sentence at two points in
time, so they take the same grammar.

## Where EARS applies

Requirements are written in EARS - the Easy Approach to Requirements Syntax. The rule for when to
reach for it is one question: **who is the subject?**

- The subject is the system, a command, a job, an endpoint - **use EARS**. It has a trigger, a
  precondition and an observable response, and EARS forces all three onto the page.
- The subject is a person, an agent or the process itself - **use the imperative or a modal**.
  'Tick a box only where evidenced', 'the reference wins', 'MUST NOT restate the spec'. Forcing
  'the system shall' onto a statement about how people work adds ceremony and loses the actor.

So specs, Validation criteria and stage acceptance conditions are EARS. Tree invariants, stage
contracts, authoring standards and this file are not.

## The six patterns

Each is a fixed shape. Picking the shape first is most of the work, because the shape names the
part you have not thought about yet.

| Pattern          | Template                                                  |
| ---------------- | --------------------------------------------------------- |
| Ubiquitous       | The `<system>` shall `<response>`.                        |
| Event-driven     | When `<trigger>`, the `<system>` shall `<response>`.      |
| State-driven     | While `<state>`, the `<system>` shall `<response>`.       |
| Optional feature | Where `<feature>`, the `<system>` shall `<response>`.     |
| Unwanted         | If `<trigger>`, then the `<system>` shall `<response>`.   |
| Complex          | Two or more of the above, preconditions first.            |

### Ubiquitous

No precondition; true on every run.

```markdown
- [ ] The importer shall record a run identifier on every record it writes.
```

Use sparingly. A criterion that is true unconditionally is often true vacuously - if you cannot
name a run where it would be observed failing, it is not a criterion.

### Event-driven versus unwanted

The split is the point of the notation, not a synonym pair. **When** introduces an expected
event; **If** introduces one you would rather did not happen. Keeping them apart forces the
failure modes to be enumerated as their own criteria instead of hiding in an 'and handles errors
gracefully' clause.

```markdown
- [ ] When a record arrives with a known identifier, the importer shall replace the stored copy.
- [ ] If a record arrives malformed, then the importer shall reject it and continue the batch.
```

### State-driven and optional feature

**While** holds throughout a state rather than firing at an instant. **Where** is for behaviour
that exists only when some feature, flag or integration is present, which is what keeps a
criterion honest about configurations it does not cover.

```markdown
- [ ] While a batch is in progress, the importer shall reject a second concurrent batch.
- [ ] Where a schema is registered, the importer shall validate each record against it.
```

### Complex

Stack the preconditions, then the trigger, then the response. If the result needs a third clause
it is usually two criteria.

```markdown
- [ ] While a schema is registered, when a record fails validation, the importer shall write it
      to the reject log with the failing field named.
```

## The right level of detail

The same three-way test as `reference-standard-spec.md`, applied to a criterion:

- **Too vague** - 'The importer shall handle bad input correctly.' Nothing is observable.
  'Correctly' is where an unverified box hides.
- **Right** - 'If a record arrives malformed, then the importer shall reject it, continue the
  batch, and report the count of rejects on completion.' A verifier can run one batch and answer.
- **Too detailed** - 'If `parse_record` raises `ValueError`, then `_ingest` shall append to
  `self._rejects` and continue the `for` loop.' This is the implementation, and it fails the
  moment the code is refactored without any behaviour changing.

The test: **could 03-verification report pass or fail on this without asking a question?** If not,
it is too vague to be a criterion.

## Writing the checkbox

- One criterion per box. A box joining two claims with 'and' cannot be half-ticked, so it gets
  ticked when the easier half passes.
- The box text is the identifier. 03-verification quotes it verbatim, so rewording a criterion
  after verification has run silently breaks the mapping between report and plan - reword during
  re-entry, not at closeout.
- State the observable, not the test. 'A unit test covers the reject path' is a task; the
  criterion is what that test asserts.
- No criterion for work that changes nothing observable. Refactors are validated by the existing
  criteria still passing, and inventing a box for them produces one that cannot fail.

## Evidence

Ticking a box at closeout appends what evidenced it, after an em dash separator:

```markdown
- [x] When a record arrives with a known identifier, the importer shall replace the stored
      copy. — `tests/test_import.py::test_replaces_known_id`
```

The citation is appended at closeout, never at authoring. The identifier is the text up to the
separator, so the rule above - the box text is what 03-verification quotes verbatim - is
untouched: renaming a test rewrites the citation and never the identifier, so the mapping
between report and plan cannot silently break. That split is what makes the convention safe.

The em dash is reserved as the separator; prose and criteria use plain hyphens, so the split is
unambiguous. Cite what a future reader would re-run - a test identifier as the stack names it,
or a command with its captured result - verbatim, because the citation is the bridge from this
frozen plan back to the automated check that keeps its spec honest.

## Deriving criteria from the spec

Each criterion traces to a spec statement or to the plan's Scope. Work through the spec delta
clause by clause and ask what run would show it working - that run is the criterion.

A criterion with no spec behind it is one of two things: scope the plan took on without declaring
it, which belongs in a spec, or a task, which belongs in Approach. Both are worth catching in
stage 01, where the fix is a paragraph rather than a re-entry.

Every `If <trigger>, then` statement in the spec is a criterion - the spec's edge cases are
enumerated in that pattern (`reference-standard-spec.md`), and each one names a run that must be
shown failing safely. A spec delta with no If clause has probably not enumerated its failures,
which is worth raising before deriving anything from it.

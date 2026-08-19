---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [YAGNI]
---

# Standard - YAGNI

'You Aren't Gonna Need It' - avoid speculative complexity. Implement only what the current task
requires.

## Principles

- Implement only what is directly requested or clearly necessary.
- Do not add features, abstractions or configuration options beyond current requirements.
- Do not add error handling for scenarios that cannot occur - validate only at system boundaries.
- Reuse existing patterns already present in the codebase over inventing new ones.
- Prefer the Standard Library over adding a dependency.
- Prefer an existing dependency over introducing a new one.
- Write the minimum code that satisfies the requirement, favouring a one-liner where it
  stays readable.
- Do not create a helper or abstraction for a one-time operation.

## Technical decisions

When a decision trades simplicity against development cost:

- Development cost SHOULD carry little weight
- Quality, simplicity, robustness and scalability SHOULD be preferred

## Specification effort

YAGNI applies to authoring too. The cost of refining a spec SHOULD stay below the cost of fixing
the misunderstanding it prevents; when that balance flips, stop polishing and build. A spec that
is not helping produce better code faster, or reducing misunderstanding, is more detailed than it
needs to be - and the remaining ambiguity is cheaper to resolve in implementation than in another
authoring pass.

This does not contradict `## Technical decisions` above. That section discounts the cost of
*writing the code* against the code's quality; this one bounds the effort spent *elaborating the
document*, which past the flip buys no code quality at all.

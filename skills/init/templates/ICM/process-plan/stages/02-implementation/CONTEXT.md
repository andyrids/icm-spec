---
context-hierarchy: Layer 2
context-hierarchy-role: Stage contract
immutable: false
recommended-context-tokens: 500
---

# Stage 02 - implementation

Bring the code into conformance with the techspec. This stage writes source and tests; it does
not renegotiate what stage 01 decided - a decision that changes observable behaviour re-enters
at 01 per the workspace re-entry rule.

## Inputs

- `../01-specification/output/<slug>-spec.md` - the techspec
- `plans/<slug>.md` - the Approach section orders the work
- `ICM/_config/reference-toolchain-*.md` - loaded per tool, only as each tool comes into play
- `ICM/_config/reference-standard-yagni.md` - the scope boundary

## Process

1. Flip `plans/<slug>.md` to `status: in-progress`.
2. Work through the techspec's implementation directives in the plan's Approach order, including
   the unit test coverage the techspec maps to Validation criteria.
3. Where reality forces a deviation from the techspec, record it in the implementation report
   with the reason - the report is the handoff, and an undocumented deviation is invisible to
   the next stage.

## Outputs

- Source and test changes
- `output/<slug>-code.md` - implementation report: files touched, deviations from the techspec,
  and anything deferred

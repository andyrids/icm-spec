---
context-hierarchy: Layer 2
context-hierarchy-role: Stage contract
immutable: false
recommended-context-tokens: 500
---

# Stage 03 - verification

Report the implementation against the plan's Validation checklist and the specs it claims
conformance with. This stage produces evidence; ticking the boxes belongs to stage 04.

## Inputs

- `plans/<slug>.md` - the Validation checklist supplies the requirement identifiers reported
  against; the `specs:` frontmatter names the conformance targets
- The `specs/**` files named in `specs:` - and only those
- `../02-implementation/output/<slug>-code.md` - deviations recorded there are checked, not
  assumed absorbed
- `ICM/_config/reference-toolchain-*.md` - loaded per tool, only as each tool comes into play

## Process

1. Run the project's test and coverage commands as the toolchain references define them, and
   capture the result verbatim.
2. Take each Validation criterion in order, quoting its checkbox text as the identifier, and
   report pass, fail or not-testable with the evidence beside it - naming the test or command
   that decided it, which is the citation stage 04 appends at ticking.
3. Compare observable behaviour against each spec named in `specs:`. A divergence is reported as
   a finding - fixing code or amending a spec is a re-entry decision, not a quiet patch here.

## Outputs

- `output/<slug>-test.md` - verification report: suite result, one entry per Validation
  criterion, and any spec divergence findings

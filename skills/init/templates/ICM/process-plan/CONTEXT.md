---
context-hierarchy: Layer 2
context-hierarchy-role: Stage routing
immutable: false
recommended-context-tokens: 500
---

# Workspace: process-plan

Stages run in order; enter a stage by reading its `CONTEXT.md`, which holds the full contract -
inputs, process and outputs.

- `process-plan/`
  - `CONTEXT.md`
  - `shared/` <- Cross-stage scratch
  - `stages/` <- 4-stage pipeline
    - `01-specification/`  <- Spec change, plan & techspec
    - `02-implementation/` <- Feature implementation
    - `03-verification/`   <- Feature testing & spec conformance
    - `04-documentation/`  <- Documentation & plan closeout

Each stage writes into its own gitignored `output/` scratch. The tracked artifacts this pipeline
produces live outside the workspace:

```text
specs/          <- Permanent contract (written in stage 01)
plans/[slug].md <- Work record (opened in 01, frozen in 04)
```

## Re-entry

A decision that changes observable behaviour returns to the earliest stage whose output it
invalidates - normally 01, because the spec and the plan must change first. Re-run only the
delta, and record the re-entry in the plan's Notes.

A linear pass that quietly patches an earlier stage's output is how a spec and its
implementation drift apart inside a single run.

## Acceptance criteria

- Artifact creation in accordance with stage guidance
- Adhere to naming convention standards
- Stage checkpoint review, over each output artifact and any changed source
- User review & acceptance MUST be explicit before continuation:
  - 'approved' or 'continue' - proceed as presented
  - approval carrying changes - apply them, and where they change observable behaviour,
    follow the re-entry rule above

A checkpoint marked *only if* is conditional. Its condition MUST be discharged with evidence in
the visible response ('216 passed, 0 failed - no gate'), so a skip is announced and can be
objected to. An unannounced skip is worse than the vacuous gate it replaces.

---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: []
---

# Standard - naming conventions

## References

| Reference      | Pattern                           | Example                          |
| -------------- | --------------------------------- | --------------------------------- |
| Toolchain      | `reference-toolchain-[tool].md`   | `reference-toolchain-mypy.md`    |
| Cookbook       | `reference-cookbook-[package].md` | `reference-cookbook-rich.md`     |
| Standard       | `reference-standard-[name].md`    | `reference-standard-techspec.md` |

## Tracked artifacts

Permanent, version-controlled. See `specs/README.md` for the state vs motion split.

| Artifact  | Pattern                      | Example                       |
| --------- | ---------------------------- | ----------------------------- |
| Command   | `specs/commands/[verb].md`   | `specs/commands/find.md`      |
| Behavior  | `specs/behaviors/[name].md`  | `specs/behaviors/cache-refresh.md` |
| Plan      | `plans/[slug].md`            | `plans/rich-progress-bar.md`  |

## Output

Ephemeral stage scratch, gitignored. The `[slug]` is shared across all four stages and is the
only thing correlating a run's artifacts - it MUST match the plan slug.

| Output                | Pattern          | Example                       |
| --------------------- | ---------------- | ------------------------------ |
| Technical spec        | `[slug]-spec.md` | `rich-progress-bar-spec.md`   |
| Implementation report | `[slug]-code.md` | `rich-progress-bar-code.md`   |
| Verification report   | `[slug]-test.md` | `rich-progress-bar-test.md`   |
| Documentation report  | `[slug]-docs.md` | `rich-progress-bar-docs.md`   |

### Frontmatter

All four open with the same Layer 4 block, whatever the stage:

```yaml
---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress   # in-progress | in-review | done
---
```

`status` tracks the artifact, not the work: `in-progress` while the stage is writing it,
`in-review` when it is presented at the stage gate, `done` once accepted. A stage that reads an
upstream output still at `in-review` is reading something the human has not signed off.

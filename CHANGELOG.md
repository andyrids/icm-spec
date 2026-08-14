<!-- pyml disable MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [!NOTE]
> Types of changes:
>
> - `Added` for new features.
> - `Changed` for changes in existing functionality.
> - `Deprecated` for soon-to-be removed features.
> - `Removed` for now removed features.
> - `Fixed` for any bug fixes.
> - `Security` in case of vulnerabilities.

## [1.0.1] - 2026-08-14

### Fixed

- `gate_spec_coverage.py` matched the porcelain status as a whole word, so a staged-then-edited
  spec (`AM`) and a `git mv`d spec (`R `) both walked past Invariant 1
- `git_pending_paths` returned a rename's `old -> new` payload as a single path, so a renamed plan
  at `status: done` with an empty `pr:` escaped `gate_closeout.py` entirely
- `git_pending_paths` was annotated `-> list[str]` while returning `(status, path)` pairs

### Changed

- `gate_spec_coverage.py` blocks a renamed spec at its destination - coverage is keyed on the
  path, so a rename leaves every plan's `specs:` entry pointing at a file that no longer exists

### Added

- `test_gates.py` covers the status column itself - `AM`, `R `, and the `old -> new` path split

## [1.0.0] - 2026-08-13

### Added

- The `icm` plugin: `/icm:init|specify|implement|verify|document` stage skills
- The `init` Layer 0 template `skills/init/templates/AGENTS.md`
- The `init` template `skills/init/templates/CHANGELOG.md`
- Marketplace config `.claude-plugin/marketplace.json`
- `/icm:express` and the `ICM/express-change/` workspace
- `ICM/_config/reference-standard-validation.md` - EARS & validation templates
- The `authors:` plan frontmatter field, for specs a plan writes without changing behaviour
- `## Specification authority` in the scaffolded `specs/README.md`
- `## Out of scope` in both spec templates
- Evidence citations at closeout
- `/icm:implement` blocks while any `[NEEDS CLARIFICATION]` marker survives in stage 01 output
- `## Specification effort` in `reference-standard-yagni.md`
- `scripts/preflight.py`, a `SessionStart` banner announcing the plugin version
- `/icm:init` checks for `uv` on `PATH` before scaffolding anything
- README documents all three install scopes - user, project, local
- `scripts/tests/check_manifest.py` asserts the version agrees everywhere it is stated
  marketplace entry declares none, since a `plugin.json` version silently masks it

### Fixed

- `gate_spec_coverage.py` accepted only `specs:`, contradicting `plans/README.md`
- Three template files had grown past the `maximum-context-tokens` budget
- `.claude-plugin/marketplace.json` no longer declares a `version`

### Changed

- Stage skills address `ICM/process-plan/`, matching the workspace name the templates scaffold
- Stage 03 loads `ICM/_config/reference-toolchain-*.md` per tool, as stage 02 already did
- `.claude-plugin/plugin.json` carries `homepage` and `repository`
- Layer 3 splits by immutability
- Layer 3 reference material carries `maximum-context-tokens: 2500`
- Plans carry their Layer 4 hierarchy keys, and `gate_plan_frontmatter.py` checks them
- Both `AGENTS.md` files state the hierarchy as the same table
- Requirements are in EARS wherever the subject is the system
- The root `CONTEXT.md` routes between two workspaces on one question - must `specs/**` change?
- The spec templates rebuilt stack-agnostic on the five-part shape (inputs, data, outputs, edge
  cases, success criteria)
- Edge cases are spec content, enumerated as EARS `If <trigger>, then` criteria under Failure
  modes or Details
- Plan Notes at closeout also preserve the *why this design* reasoning, which otherwise lives
  only in the techspec and is deleted with the run's scratch

### Removed

- `examples/` pointers from the scaffolded `specs/README.md` and `plans/README.md`

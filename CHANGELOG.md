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

## [1.2.0]

### Added

- `gate_spec_frontmatter` - a PostToolUse gate that feeds context back when a written spec has
  no frontmatter block or a missing or wrong Layer 3 hierarchy key (#18)
- A `## Frontmatter` section in `specs/README.md`, the contract the new gate cites (#18)

### Changed

- `maximum-context-tokens` is renamed `recommended-context-tokens` across the frontmatter
  contract - the layer budgets are guidance, not a build-breaking limit
- `AGENTS.md` reframes the token budget bullet from an enforced ceiling to a signal worth a look

### Removed

- `check_budgets.py` and its `just test-budgets` recipe - a pass/fail test no longer fits a
  recommendation rather than a constraint

### Fixed

- Both spec templates in `reference-standard-spec.md` opened on the H1 with no frontmatter, so a
  spec authored by following them broke the Layer 0 rule that every tabled file carries
  `context-hierarchy`, `context-hierarchy-role` and `immutable` (#18)
- `AGENTS.md` tabled the Layer 3 role for `specs/**/*.md` as `Desired state`, disagreeing with
  the README and with a value used nowhere else in the tree - it is `Reference material` (#18)

## [1.1.0] - 2026-08-15

### Fixed

- `git_pending_paths` read git C-quoted octal escapes as path separators, mangling any
  non-ASCII path - it now reads `git status --porcelain -z`, which never quotes (#6)
- `git_pending_paths` decoded `git status` output in the locale codepage rather than UTF-8 (#6)
- Quoted `specs:`/`authors:` frontmatter entries kept their quote characters, so a plan written
  in ordinary YAML read as owning no spec and `gate_spec_coverage` blocked the Stop naming a
  spec the plan owned (#9)
- A non-UTF-8 file raised `UnicodeDecodeError` out of four gates and `preflight.py`, so one
  unreadable plan stopped every other plan being judged (#8)

### Changed

- Replaced `scripts/tests/test_gates.py` with a layered `unittest` package (`scripts/tests/`)
- `check_manifest.py` no longer checks the README, which restates no version

## [1.0.1] - 2026-08-14

### Fixed

- `gate_spec_coverage.py` matched the porcelain status as a whole word
- `git_pending_paths` returned a rename's `old -> new` payload as a single path
- `git_pending_paths` was annotated `-> list[str]` while returning `(status, path)` pairs

### Changed

- `gate_spec_coverage.py` previously blocked a renamed spec at its destination

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

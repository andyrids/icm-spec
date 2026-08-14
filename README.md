# ICM Plugin Handbook

`icm` is a Claude Code plugin that runs spec-driven development (spec-anchored) as a staged
pipeline with human review gates, on top of Interpretable Context Methodology (ICM).

With spec-anchored development, a specification evolves alongside the software and is updated to
reflect the current state of the system as it changes. Adverserial agent verification is used to
automate spec-drift detection.

ICM replaces framework-level orchestration with filesystem structure. Numbered folders represent
stages. Plain markdown files carry prompts and context that tell a single AI agent what role to
play at each step.

> [!IMPORTANT]
> Concepts adapted from an Interpretable Context Methodology paper attributed to Van Clief, J.
> and McDermott, D., 2026 (arXiv:2603.16021).

A large community dedicated to this methodology can be found at
[https://www.skool.com/cliefnotes](https://www.skool.com/cliefnotes/about?ref=478219c6d94340bd984dde6a8d1046e6).

A community member made a detailed and easy-to-understand video guide on YouTube -
[here](https://youtu.be/tvvaOCK_Z50?si=dX86mhIKVEXSVM0k).

---

## Premise - What the plugin actually does

An agent with a large context window often reads and decides everything at once, causing a spec,
its implementation and its record to drift inside a single session.

ICM forces these components apart. Work moves through **stages**, each with a written contract
naming what it reads, what it does and what it writes and between these stages sits a human.

The plugin supplies the folder structure that define this, the commands that enter each
stage and hook **gates** that make the rules refuse rather than simply advise.

Three ideas carry the whole design and everything below details their implementation.

### State, motion, scratch

- `specs/` - What MUST be true about the project (forever).
- `plans/` - Steps taken to realise specs (frozen when done).

Stage output is scratch (ephemeral), gitignored. Confusing the three is the failure this tree
exists to prevent.

### Contracts cite, references state

A stage contract points at the rule it depends on rather than restating it. Where a stage and a
reference disagree, the reference wins and the contract is what needs fixing.

### The record is not optional

Every unit of work leaves a plan file, including small ones. The fast path is a shorter pipeline,
never a plan-free one - skipping the record hollows it out.

### Configure the factory

The templates are stack-agnostic. Anything specific to a language, test runner or linter goes in a
`reference-toolchain-*.md` file, not in the pipeline.

---

## Setup - Installing and scaffolding

### Requirements

Two tools, both on `PATH`.

#### (1) `uv`

Every hook runs as a single-file Python script through `uv run`. `uv` supplies Python itself,
mitigating system Python installation.

#### (2) `git`

`git status` is used to reason about work in flight.

### Installing

Add the marketplace, then install the plugin:

```sh
/plugin marketplace add andyrids/icm-spec
```

```sh
/plugin install icm@icm-spec
```

Scaffold the tree into the repository you are standing in:

```sh
/icm:init
```

`/plugin install` prompts for a scope (all compatible) - the gates guard themselves by looking for
`ICM/`.

1. **User** enables the plugin in every project - relying on guards for non-ICM projects.
2. **Project** writes `.claude/settings.json` - shared with the repository.
3. **Local** is the private project form - unshared.

Non-interactively - `claude plugin install icm@icm-spec --scope project`.

A repository can pre-declare the plugin, causing a prompt to install it, the moment the folder
is trusted via `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "icm-spec": { "source": { "source": "github", "repo": "andyrids/icm-spec" } }
  },
  "enabledPlugins": { "icm@icm-spec": true }
}
```

> [!NOTE]
> `/icm:init` is idempotent - existing destination files are untouched and reported as `exists`, so
> re-running after an update is safe.

### Updating

An update has two steps because the catalog and plugin are cached separately:

1. `/plugin marketplace update icm-spec` - re-fetches the catalog.
2. `/plugin update icm@icm-spec` - installs the new version.

Claude Code caches an installed plugin under marketplace, plugin and version and a scope only
records *enablement* in its settings. Updating is one operation that every scope sees, not
three.

Auto-update is off by default for third-party marketplaces - only official Anthropic
marketplaces automatically update. Turn it on per marketplace under:

`/plugin` → **Marketplaces** → **Enable auto-update**, or carry `"autoUpdate": true` on the
`extraKnownMarketplaces` entry shown above.

After a mid-session update, run `/reload-plugins` and `${CLAUDE_PLUGIN_ROOT}` points at the new
version.

Updating the plugin never touches an existing tree. `/icm:init` reports `exists` for every file
already present and moves on. It will not overwrite a `reference-*.md` you have amended.

> [!IMPORTANT]
> Reconciling a scaffolded tree with newer templates is a manual diff.

### What lands in the repository

```text
AGENTS.md        <- Layer 0 - project identity + hierarchy (CLAUDE.md symlinks)
CONTEXT.md       <- Layer 1 - routes to a workspace, and nothing deeper
CHANGELOG.md     <- Keep a Changelog stub
.gitignore       <- Ignores stage output/ and shared/ scratch

specs/
  README.md      <- Tree layout, the four invariants, the ripple protocol

plans/
  README.md      <- Frontmatter contract, section order, closeout steps

ICM/
  _config/                            <- Layer 3 reference material
    reference-standard-spec.md        <- How to author a spec
    reference-standard-validation.md  <- EARS patterns for Validation criteria
    reference-standard-techspec.md    <- The techspec template
    reference-standard-naming.md      <- Slugs, filenames, output frontmatter
    reference-standard-markdown.md    <- Prose and typography conventions
    reference-standard-changelog.md   <- Keep a Changelog rules
    reference-standard-yagni.md       <- The scope boundary

  process-plan/   <- The four-stage pipeline
    CONTEXT.md
    shared/
    stages/
      01-specification/
      02-implementation/
      03-verification/
      04-documentation/

  express-change/  <- The one-stage pipeline
    CONTEXT.md
    stages/
      01-change/
```

> [!NOTE]
> The top of `AGENTS.md` carries a `[Project name]` placeholder block, which `init` deliberately
> leaves unfilled. Replace it with what the project is, who it serves and one or two important
> constraints.

---

## Structure - The five context layers

Every markdown file the methodology owns declares its layer in frontmatter. The layer says what
kind of thing the file is and, crucially, **when it may be loaded**.

### Layer 0

Who this project is, plus the hierarchy itself. Read once, at the start of everything.

- Category: Structural routing
- Role: Global identity
- Path:
  - `AGENTS.md`
- Frontmatter:
  - `context-hierarchy` (Layer 0)
  - `context-hierarchy-role` (Global identity)
  - `immutable` (false)
  - `maximum-context-tokens` (900)

### Layer 1

Matches the work to a pipeline and stops. Its whole job is to send you one level deeper.

- Category: Structural routing
- Role: Workspace routing
- Path:
  - `CONTEXT.md`
- Frontmatter:
  - `context-hierarchy` (Layer 1)
  - `context-hierarchy-role` (Workspace routing)
  - `immutable` (false)
  - `maximum-context-tokens` (300)

### Layer 2

A workspace's shape and each stage's inputs, process and outputs. The contract is the authority for
its stage.

- Category: Structural routing
- Role: Stage routing
- Path:
  - `ICM/*/CONTEXT.md`
  - `ICM/*/stages/**/CONTEXT.md`
- Frontmatter:
  - `context-hierarchy` (Layer 2)
  - `context-hierarchy-role` (Stage routing)
  - `immutable` (false)
  - `maximum-context-tokens` (500)

### Layer 3

Two roles share this layer. Reference material is the factory configuration and is
`immutable: true`, budgeted at 2500 tokens. Specs are `immutable: false` and unbudgeted - the
pipeline exists to amend them and a spec is as long as the behaviour it declares.

- Category: Content
- Role: Reference material
- Path:
  - `specs/**/*.md`
  - `ICM/_config/reference-*`
- Frontmatter:
  - `context-hierarchy` (Layer 3)
  - `context-hierarchy-role` (Reference material)
  - `immutable` (true | false)
  - `tags` ([keyword, ...])

### Layer 4

Things the pipeline produces. Plans are tracked and frozen at closeout; stage output is ephemeral
scratch, rebuilt per run.

- Category: Content
- Role: Working artifact
- Path:
  - `plans/*.md`
    - Frontmatter:
      - `context-hierarchy` (Layer 4)
      - `context-hierarchy-role` (Working artifact)
      - `immutable` (false)
      - `status` (planned | in-progress | done | blocked | cancelled)
  - `ICM/*/stages/**/output/*.md`
    - Frontmatter:
      - `context-hierarchy` (Layer 4)
      - `context-hierarchy-role` (Working artifact)
      - `immutable` (false)
      - `status` (in-progress | in-review | done)

---

## Routing - Two pipelines, one question

`CONTEXT.md` offers two workspaces, and choosing between them is a single question:

**must `specs/**` change?**

If yes - new behaviour, changed behaviour or a rule not yet declared - it is `process-plan`,
however small the diff looks.

If no and the work is a single commit, it is `express-change`. Size is not the test as a simple
diff that changes what the software promises is a spec change - unlike a large refactor that
changes nothing observable.

### process-plan - four stages

- **Stage 01 - Specification** - Turns a request into a spec change, a plan at `status: planned`
and a techspec. Nothing is implemented.
- **Stage 02 - Implementation** - Brings code into conformance with the techspec. Deviations are
recorded, not absorbed silently.
- **Stage 03 - Verification** - Reports each plan validation criterion against captured test output
and compares behaviour to every spec in `specs:`.
- **Stage 04 - Documentation** - `CHANGELOG.md` entry, plan closeout, follow-ups.

Each stage ends at an unconditional review gate, presenting its output and waiting for explicit
acceptance. "Approved" or "continue" proceeds as presented; approval carrying changes applies them
and where they change observable behaviour, the **re-entry rule** sends the work back to the
earliest stage whose output is now invalid (normally 01), because the spec and the plan must move
first.

> [!TIP]
> Only the delta is re-run and the re-entry is recorded under the plan `## Notes`.

### express-change - one stage

The same run compressed: eligibility, change, evidence, closeout, with a single review gate at the
end. It drops the techspec and the three intermediate reports as those exist to carry decisions
between stages, which is not required here.

**Why the fast path cannot be abused:** eligibility requires that **no spec has to change**.
Needing a spec change is what makes work NOT small, so the condition cannot be satisfied by work
that requires stage 01.

The agent must evidence an eligibility verdict *before* writing anything, so a wrong call gets
denied rather than discovered afterwards.

> [!TIP]
> If scope grows mid-run, that signals the wrong call was made.

---

## Walkthrough - A change from request to frozen record

This details a full pipeline for a feature that changes what the software promises. Assume a
scaffolded repository on a feature branch.

### (1) `/icm:specify add a --json output mode to the CLI report command`

Stage 01 reads Layer 1, then the workspace, then its own contract - and only the references
that contract names. It picks a kebab-case slug (`json-output-mode`) that will correlate every
artifact this run produces.

It writes or amends the spec under `specs/`. That write triggers `ask` from `gate_spec_edit` - you
approve it, which is the point: spec changes are never silent.

It then opens `plans/json-output-mode.md` at `status: planned` and drafts the techspec into
stage 01 gitignored `output/`.

Anything genuinely undecided is marked `[NEEDS CLARIFICATION: <question>]` rather than guessed.

*REVIEW GATE* - You see the spec diff, the plan and the techspec. This is the cheapest place to
disagree.

### (2) `/icm:implement`

Before the command even reaches the model, `gate_implement` checks that a plan exists at `planned`
or `in-progress`. If none, the command is blocked outright - there is nothing to implement against.

The stage flips the plan to `in-progress` and works through the techspec directives in the Approach
order, writing source and tests.

Where reality forces a deviation from the techspec, it records the deviation and the reason in the
implementation report, because the report is the handoff and undocumented deviations are invisible
to stage 03.

*REVIEW GATE* - The implementation report, plus the diff.

### (3) `/icm:verify`

Runs the project tests and coverage commands as your `reference-toolchain-*.md` files define them
and captures the result verbatim. It then walks the validation checklist in order, quoting each
checkbox as the requirement identifier and reports evidenced pass, fail or not-testable beside it.

Finally, it compares observable behaviour against each spec named in `specs:`. A divergence is
*reported*, not fixed.

> [!WARNING]
> Fixing code or amending a spec is a re-entry decision, not a quiet patch.

*REVIEW GATE* - The verification report.

### (4) `/icm:document`

Adds a `CHANGELOG.md` entry under `[unreleased]`, then closes the plan out:

- `status: done`
- `pr:` set
- Validation boxes ticked *only* where stage 03 produced evidence.

> [!NOTE]
> An unticked box with a reason in Notes beats a ticked one that was never checked and
> `gate_closeout` enforces exactly that trade.

Follow-ups are recorded against a fixed taxonomy and a `Deferred to` entry must edit the named
downstream plan in the same commit - otherwise the deferral is a non-binding pointer and the work
is lost between two documents that each assume the other owns it.

*The run ends here.* The frozen plan, the amended spec and the changelog entry are what survive;
everything in `output/` was scratch.

### The same fix, express

```sh
/icm:express the report command crashes on an empty result set
```

One command, one gate. The agent first states why no spec has to change - the spec already declares
the empty-result behaviour and the code diverges from it, which Invariant 2 calls a bug rather than
a change.

Then it opens the plan, makes the fix, runs the suite, reports each Validation criterion,
closes the plan and adds the changelog entry and presents all of it at once.

---

## Artifacts - Specs, plans and the frontmatter that is queried

### The three artifact kinds

| Kind | Answers | Location | Lifetime |
|---|---|---|---|
| Spec | What must be true, forever | `specs/**` | Permanent, changed by review |
| Plan | What we are doing about it | `plans/<slug>.md` | Frozen at `status: done` |
| Techspec | How, in implementation terms | stage `output/` | Ephemeral scratch, gitignored |

### Plan frontmatter

Nothing maintains a status table or a dependency diagram, because both rot the moment someone
forgets to update them. The frontmatter is the query surface instead, and every coverage and
ripple check reads it.

```yaml
---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: planned        # planned | in-progress | done | blocked | cancelled
depends: []            # other plan slugs that must land first
specs:                 # specs this plan brings CODE into conformance with
  - specs/commands/report.md
authors: []            # specs this plan WRITES, with no behaviour change
issues: []
pr:                    # set at closeout
---
```

> [!IMPORTANT]
> `specs:` and `authors:` answer different questions and a spec belongs in exactly one. `specs:`
> claims this plan changes code until it conforms. `authors:` claims the plan writes the spec and
> changes no behaviour; nothing is verified against it.

### Plan body

Fixed section order: **Scope**, **Implements**, **Approach**, **Validation**, **Risks / unknowns**,
**Notes**, **Follow-ups**. Notes and Follow-ups stay empty until closeout.

**Validation** is load-bearing. It is the checkbox list that converts `in-progress` to `done`, it
supplies the requirement identifiers stage 03 reports against, and `gate_closeout` parses it. Its
checkbox text *is* the identifier, so rewording a criterion after verification has run silently
breaks the mapping between report and plan.

### The four spec invariants

1. Every spec on the default branch is implemented, or owned by a committed plan through `specs:`
or `authors:`.
2. Spec/code divergence is a bug, not debt. Fix the code or amend the spec.
3. A spec still being negotiated stays off the default branch until its plan rides along with it.
4. Where the project has a CLI, `--help` is authoritative for invocation.

After amending a spec, run the ripple check - `grep -l '<spec path>' plans/*.md` - and flag the
plans chasing old desired state.

A `planned` plan may need its scope revised; an `in-progress` plan is flagged, never silently
rewritten.

---

## Enforcement - The seven gates, and what each one feels like

Gates are hook scripts. They read one event on stdin and answer with an exit code or a JSON
decision.

Exit 2 is a hard block; anything unexpected degrades to exit 0, so a broken gate can never wedge a
session. Every gate no-ops entirely when there is no `ICM/` directory - its hooks must stay silent
in unrelated repositories that happen to own a `specs/` folder.

### Gate reference

- **`gate_implement`**
  - *Fires on*: prompt expansion
  - *Effect*: block
  - *What it protects*: `/icm:implement` refuses to expand with no plan at `planned` or
    `in-progress`. Stage 02 implements an *accepted* plan
- **`gate_clarification`**
  - *Fires on*: prompt expansion
  - *Effect*: block
  - *What it protects*: `/icm:implement` refuses to expand while a `[NEEDS CLARIFICATION: ...]`
    marker survives in stage 01 output. Implementing over an open question means guessing its
    answer
- **`gate_spec_edit`**
  - *Fires on*: write to `specs/`
  - *Effect*: ask
  - *What it protects*: Never a hard deny - spec amendment is legitimate stage 01 or re-entry
    work. You are the gate
- **`gate_output_naming`**
  - *Fires on*: write to `ICM/`
  - *Effect*: deny
  - *What it protects*: Stage output must be `<slug>-spec\|code\|test\|docs.md` with the suffix
    its stage owns. The slug is the only thing correlating a run's artifacts
- **`gate_plan_frontmatter`**
  - *Fires on*: after a plan write
  - *Effect*: advise
  - *What it protects*: Cannot block; feeds context back on an invalid `status`, an unresolvable
    spec path, a spec in both list fields, or a missing Layer 4 key
- **`gate_spec_coverage`**
  - *Fires on*: session stop
  - *Effect*: block
  - *What it protects*: A spec new to the tree that no plan owns - untracked, staged, or
    arriving at a new path by rename. A merely modified spec is never blocked; that is the
    ripple protocol's job, and blocking would punish typo fixes
- **`gate_closeout`**
  - *Fires on*: session stop
  - *Effect*: block
  - *What it protects*: A plan at `done` with no `pr:`, or unticked Validation boxes with an
    empty Notes section

### When a Stop gate blocks you

Both Stop gates read uncommitted state, so the fix is always to complete the record rather than to
argue with the hook. Coverage blocking means a new spec has no owner: add it to the owning plan's
`specs:` if code must change, or its `authors:` if the plan only wrote it. A rename blocks for the
same reason and takes the same fix in a different direction: the destination path is a spec no
plan names, so move the owning plan's `specs:` entry to the new path - the record went stale the
moment the file did. Closeout blocking means
the plan froze half-closed: set `pr:`, or write into Notes *why* each unticked box stays unticked.
Neither gate is asking you to do more work than the protocol already required - only to do it
before the session ends.

---

## Authoring - How requirements are written

Statements about system behaviour use EARS - the Easy Approach to Requirements Syntax. The rule for
when it applies is one question: **who is the subject?**

If the subject is the system, a command, a job or an endpoint, use EARS. If it is a person, an
agent or the process itself, use an imperative or a modal. Forcing "the system shall" onto a
statement about how people work adds ceremony and loses the actor.

> [!TIP]
> Specs, Validation criteria and stage acceptance conditions are EARS; tree invariants, stage
> contracts and authoring standards are not.

### The six patterns

- **Ubiquitous**: Always true, no precondition
  - *Template*: `The <system> shall <response>.`
- **Event-driven**: An expected event
  - *Template*: `When <trigger>, the <system> shall…`
- **State-driven**: Holds throughout a state
  - *Template*: `While <state>, the <system> shall…`
- **Optional feature**: Behaviour that exists only in some configurations
  - *Template*: `Where <feature>, the <system> shall…`
- **Unwanted**: An event you would rather did not happen
  - *Template*: `If <trigger>, then the <system> shall…`
- **Complex**: Two or more of the above
  - *Template*: Preconditions, then trigger, then response

The **When** / **If** split is the point of the notation, not a synonym pair. Keeping them apart
forces failure modes to be enumerated as their own criteria rather than hiding inside an "and
handles errors gracefully" clause.

```markdown
- [ ] When a record arrives with a known identifier, the importer shall replace
      the stored copy.
- [ ] If a record arrives malformed, then the importer shall reject it and
      continue the batch.
```

The test for a criterion is whether stage 03 could report pass or fail on it without asking a
question. One criterion per box - a box joining two claims with "and" cannot be half-ticked,
so it gets ticked when the easier half passes.

---

## Support - The pieces that run without being called

### Path-scoped skills

Two skills, `spec` and `plan`, are scoped to `specs/**` and `plans/**`. They load automatically
when work touches those trees and carry only the rules that bite most often, pointing at the full
protocol rather than restating it. They are the reason an agent editing a plan outside a stage
still gets the frontmatter contract right.

### The drift auditor

`spec-drift-auditor` is a read-only agent. It changes nothing and produces three tables: specs with
no covering plan, plans chasing specs that have since been amended, and spec/code divergence. It
verifies each divergence adversarially before reporting - re-reading the exact spec lines and code
paths and attempting to prove the conflict wrong - and reports only what survives, naming which
side it judges to be in error.

Run it after a batch of merges, or whenever you suspect the record and the code have drifted apart.

### Toolchain references

The pipeline never names a language, test runner or linter. Stages 02, 03 and the express stage
load `ICM/_config/reference-toolchain-*.md` per tool, only as each tool comes into play. These are
yours to add as the project acquires them - one file per tool, following the naming standard. Until
you write one, "run the project's test and coverage commands as the toolchain references define
them" has nothing to define it, which is the honest state of a project that has not yet said how it
is tested.

---

## Maintenance - Keeping the tree honest

Tests can be run with the Justfile recipe - `just test` or manually, with the following commands:

```sh
uv run --no-project python -m unittest discover -s scripts/tests -t scripts -v
uv run --no-project python scripts/tests/check_paths.py
uv run --no-project --script scripts/tests/check_budgets.py
uv run --no-project --script scripts/tests/check_manifest.py
```

- **`scripts/tests/`**: A `unittest` package (run via `python -m unittest discover`) proving
  every gate blocks the case it should *and* opens for the case it should - a gate that never
  opens is as broken as one that never closes. Three layers: pure functions in-process, `main()`
  against real git fixtures, and one real subprocess per script pinning the deployed contract
- **`check_paths.py`**: Every backtick-quoted path a scaffolded tree cites in prose resolves.
  Deliberate forward references are allowlisted with their reason, so an unexplained addition
  is the smell
- **`check_budgets.py`**: No file exceeds the `maximum-context-tokens` its own frontmatter
  declares and warns at 90%
- **`check_manifest.py`**: The version agrees everywhere it is stated - `plugin.json`, the
  README header, the CHANGELOG release heading - and the marketplace entry declares none,
  because a manifest version silently masks it

`check_paths.py` takes an optional path argument, so you can point it at your own project rather
than the templates - useful after you have added specs and reference files of your own.

One platform note: this repository's `CLAUDE.md` is a symlink to `AGENTS.md`. A Windows clone
without `core.symlinks=true` materialises it as a one-line text stub instead; `just symlink-agents`
restores the link.

### Adding a workspace

A new deliverable does not need a new workspace. Copy an existing pipeline only when a genuinely
different *shape* is required - which is exactly what justified `express-change` existing as a
workspace rather than as a flag on `process-plan`.

A new workspace needs a Layer 2 `CONTEXT.md`, a Layer 2 contract per stage, and one entry in the
Layer 1 router with the question that selects it.

---

## Reference - Every command

| Command | Argument | Does |
|---|---|---|
| `/icm:init` | - | Scaffolds the tree. Idempotent; reports `written` or `exists` per file |
| `/icm:specify` | feature request | Stage 01. Spec change, plan, techspec |
| `/icm:implement` | plan slug, optional | Stage 02. Source, tests, implementation report |
| `/icm:verify` | plan slug, optional | Stage 03. Evidence against every Validation criterion |
| `/icm:document` | plan slug, optional | Stage 04. Changelog, closeout, frozen plan |
| `/icm:express` | change request | The one-stage pipeline, for work no spec has to move for |

All six are user-invoked only - they carry `disable-model-invocation: true`, so the model cannot
enter a stage on its own initiative. Entering a pipeline is your decision, every time. Where the
slug argument is optional, an unambiguous open plan is used and you are asked when it is ambiguous.

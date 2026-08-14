---
name: init
description: >
   Scaffold the ICM tree into the current repository - AGENTS.md, CONTEXT.md, CHANGELOG.md, ICM/,
   specs/, plans/ and .gitignore
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Glob, Bash
---

# Scaffold ICM into this repository

First, run `uv --version` through Bash. If it fails, stop and scaffold nothing: every gate this
plugin ships runs through `uv`, and a gate that cannot start is treated as a non-blocking error,
so the tree would carry enforcement that silently fails open. Tell the user to install `uv`
(<https://docs.astral.sh/uv/getting-started/installation/>) and re-run `/icm:init`.

Then copy the tree under `${CLAUDE_SKILL_DIR}/templates/` into the repository root. The
operation is idempotent: a destination file that already exists is left untouched, and
re-running reports `exists` per file rather than rewriting anything.

Mapping, template path to destination:

| Template                  | Destination            |
| ------------------------- | ---------------------- |
| `AGENTS.md`               | `AGENTS.md`            |
| `CONTEXT.md`              | `CONTEXT.md`           |
| `CHANGELOG.md`            | `CHANGELOG.md`         |
| `gitignore`               | `.gitignore`           |
| `specs/README.md`         | `specs/README.md`      |
| `plans/README.md`         | `plans/README.md`      |
| `ICM/**` (all files)      | `ICM/**`               |

Then:

1. If `.gitignore` already existed, append any template lines it is missing (the stage `output/`
   ignore is load-bearing) instead of overwriting.
2. Point `CLAUDE.md` at `AGENTS.md`: create a symlink where the platform allows it, otherwise
   write a `CLAUDE.md` containing only `@AGENTS.md`.
3. Copy every `output/.gitkeep` and `shared/.gitkeep` so the empty directories survive a clone.
4. Report one line per file - `written` or `exists` - and finish by naming the two entry points:
   `/icm:specify <feature request>` for work that changes what `specs/**` declares, and
   `/icm:express <change request>` for work that conforms to a spec already committed. The root
   `CONTEXT.md` is the authority on choosing between them.

Do not tailor the copied files to the project during init. They are the factory configuration;
project-specific reference material (`ICM/_config/reference-toolchain-*.md`) is added by the
user as tools come into play.

The one exception is the `[Project name]` identity block at the top of `AGENTS.md`, which is a
placeholder rather than configuration. Leave it as written and tell the user it is theirs to fill
in - an unfilled identity block is visible, whereas a guessed one is not.

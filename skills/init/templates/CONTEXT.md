---
context-hierarchy: Layer 1
context-hierarchy-role: Workspace routing
immutable: false
recommended-context-tokens: 300
---

# Workspace routing

Two workspaces. Match the work to a pipeline, then read that workspace's `CONTEXT.md` - nothing
deeper until a stage is entered.

## Workspaces

### process-plan

- **Work**: a spec change, its implementation, verification and closeout
- **Read**: `ICM/process-plan/CONTEXT.md`

### express-change

- **Work**: a change conforming to a spec already on the default branch, landing in one commit
- **Read**: `ICM/express-change/CONTEXT.md`

## Choosing

One question decides it: **must `specs/**` change?** If yes - new or changed behaviour, or a rule
not yet declared - it is `process-plan`, however small the diff looks. If no, and the work is one
commit's worth, it is `express-change`.

Size is not the test. A two-line diff that changes what the software promises is a spec change; a
large mechanical refactor that changes nothing observable is not.

## Shared configuration

Standards shared by every workspace live in `ICM/_config/` as `reference-*.md` files (Layer 3).
Load one only when its subject is in play. A new deliverable does not need a new workspace -
configure the factory, not the product.

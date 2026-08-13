[unix]
set shell := ["bash", "-euo", "pipefail", "-c"]

[windows]
set shell := ["cmd.exe", "/c"]

set dotenv-load := true

[default]
@_:
    just --list

[doc("Run every check")]
[group("TEST")]
test: test-gates test-paths test-budgets test-manifest

[doc("Unit tests for the seven hook gates")]
[group("TEST")]
test-gates:
    uv run --no-project python scripts/tests/test_gates.py

[doc("Every path a scaffolded tree cites in prose resolves")]
[group("TEST")]
test-paths:
    uv run --no-project python scripts/tests/check_paths.py

[doc("Every declared maximum-context-tokens budget is respected")]
[group("TEST")]
test-budgets:
    uv run --no-project --script scripts/tests/check_budgets.py

[doc("The version agrees everywhere it is stated")]
[group("TEST")]
test-manifest:
    uv run --no-project --script scripts/tests/check_manifest.py

[doc("Git prune (aggressive)")]
[group("DEV")]
git-prune:
    git gc --prune=now --aggressive

[doc("Git prune (aggressive)")]
[group("DEV")]
symlink-agents:
    @uv run python -c "import pathlib; p=pathlib.Path('CLAUDE.md'); p.unlink(missing_ok=True); p.symlink_to('AGENTS.md')"

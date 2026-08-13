# /// script
# requires-python = ">=3.10"
# dependencies = ["tiktoken"]
# ///
"""Check every file declaring `maximum-context-tokens` against its own budget.

The budget is the layer contract's one measurable clause, and until this
existed nothing measured it - three template files had quietly grown past
theirs. A ceiling nobody checks is a comment.

Counts with `cl100k_base`, which is not the tokenizer Claude uses. That is
fine and deliberate: the budget is a design constraint on how much a routing
file may say, not a hard API limit, so a stable approximation applied
consistently answers the question 'has this file started doing another
layer's job?'. A dependency-free character estimate does not - measured
against this corpus it ranges from 3.75 to 5.18 characters per token, wide
enough to fail a compliant file.

Run: uv run --no-project --script scripts/tests/check_budgets.py [path]

License:
    SPDX-License-Identifier: Apache-2.0
"""

import re
import sys
from pathlib import Path

import tiktoken

BUDGET = re.compile(r"^maximum-context-tokens:\s*(\d+)\s*$", re.M)
# Warn before a file breaches, so the fix is a sentence rather than a rewrite.
NEAR = 0.9


def main() -> int:
    """Main entry point for the check."""
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    encoding = tiktoken.get_encoding("cl100k_base")
    over, near, checked = [], [], 0
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        match = BUDGET.search(text)
        if not match:
            continue
        # A CLAUDE.md symlinked at AGENTS.md is the same file twice.
        if path.name == "CLAUDE.md" and path.is_symlink():
            continue
        checked += 1
        budget = int(match.group(1))
        count = len(encoding.encode(text))
        rel = path.relative_to(root).as_posix()
        if count > budget:
            over.append((count, budget, rel))
        elif count > budget * NEAR:
            near.append((count, budget, rel))
    for count, budget, rel in over:
        print(f"  OVER  {count:>5} / {budget:<5} {rel}")
    for count, budget, rel in near:
        print(f"  near  {count:>5} / {budget:<5} {rel}")
    print(f"\n{checked} budgeted documents checked, {len(over)} over budget")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())

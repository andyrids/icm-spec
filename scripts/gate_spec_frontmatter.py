# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: spec frontmatter stays routable.

Event: PostToolUse (Edit|Write) - cannot block; feeds `additionalContext`
back when a written spec has no frontmatter block, or a missing or wrong
Layer 3 hierarchy key. The block is what places the file in the context
hierarchy, so a spec without it is unroutable by layer - loaded by whoever
happens to open it rather than by the stage the layer contract assigns.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys
from pathlib import Path

from _common import (
    SPEC_HIERARCHY,
    emit,
    is_icm_project,
    parse_hierarchy,
    project_dir,
    read_event,
    relative_posix,
)


def main() -> int:
    """Main entry point for the gate."""
    event = read_event()
    file_path = str(event.get("tool_input", {}).get("file_path", ""))
    if not file_path:
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    rel = relative_posix(file_path, root)
    # No depth constraint, unlike the plan gate: specs nest
    # (`specs/commands/find.md`) and `specs/principles.md` is flat, and both
    # are in scope. `specs/README.md` is excluded because it is Layer 3
    # reference material at `immutable: true` with a budget - a different
    # schema, held by its own contract rather than this one.
    if (
        rel is None
        or not rel.startswith("specs/")
        or not rel.endswith(".md")
        or rel == "specs/README.md"
    ):
        return 0
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    # ValueError included (issues #8, #17): it covers UnicodeDecodeError for
    # an undecodable file and the embedded-NUL path that only raises inside
    # read_text - both must degrade to no verdict rather than crash a
    # PostToolUse hook that cannot block anyway.
    except (OSError, ValueError):
        return 0
    problems = []
    meta = parse_hierarchy(text, SPEC_HIERARCHY)
    if meta is None:
        problems.append("no YAML frontmatter block")
    else:
        # `tags` is deliberately unchecked: it aids retrieval, and a gate
        # demanding keywords would invite placeholder ones.
        for key, expected in SPEC_HIERARCHY.items():
            if meta[key] is None:
                problems.append(f"{key}: is missing (expected '{expected}')")
            elif meta[key] != expected:
                problems.append(
                    f"{key}: is '{meta[key]}', expected '{expected}'"
                )
    if not problems:
        return 0
    emit(
        "PostToolUse",
        additionalContext=(
            f"{rel} has invalid spec frontmatter ({'; '.join(problems)}). The frontmatter "
            "contract is in specs/README.md; fix it now, because the block is what makes "
            "the spec routable by layer."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

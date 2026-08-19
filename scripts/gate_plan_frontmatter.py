# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: plan frontmatter stays queryable.

Event: PostToolUse (Edit|Write) - cannot block; feeds `additionalContext`
back when a written plan has a missing or invalid frontmatter block, a
`status` outside the enum, a `specs:` or `authors:` entry that does not
resolve to a file, a spec claimed by both fields at once, or a missing Layer 4
hierarchy key. The frontmatter is the query surface every coverage and ripple
check reads, so an invalid value silently drops the plan out of every query.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys
from pathlib import Path

from _common import (
    EXPECTED_HIERARCHY,
    LIST_KEYS,
    STATUS_ENUM,
    emit,
    is_icm_project,
    parse_plan_frontmatter,
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
    if (
        rel is None
        or not rel.startswith("plans/")
        or rel.count("/") != 1
        or not rel.endswith(".md")
        or rel == "plans/README.md"
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
    meta = parse_plan_frontmatter(text)
    if meta is None:
        problems.append("no YAML frontmatter block")
    else:
        if meta["status"] not in STATUS_ENUM:
            problems.append(
                f"status '{meta['status']}' is not one of: {', '.join(sorted(STATUS_ENUM))}"
            )
        for key, expected in EXPECTED_HIERARCHY.items():
            if meta[key] is None:
                problems.append(f"{key}: is missing (expected '{expected}')")
            elif meta[key] != expected:
                problems.append(
                    f"{key}: is '{meta[key]}', expected '{expected}'"
                )
        for key in LIST_KEYS:
            for spec in meta[key]:
                if not (root / spec).is_file():
                    problems.append(
                        f"{key}: entry '{spec}' does not resolve to a file"
                    )
        for spec in set(meta["specs"]) & set(meta["authors"]):
            problems.append(
                f"'{spec}' is in both specs: and authors: - a spec whose code this plan "
                "brings into conformance belongs in specs: alone"
            )
    if not problems:
        return 0
    emit(
        "PostToolUse",
        additionalContext=(
            f"{rel} has invalid plan frontmatter ({'; '.join(problems)}). The frontmatter "
            "contract is in plans/README.md; fix it now, because every coverage and ripple "
            "query reads it."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: a plan cannot freeze half-closed.

Event: Stop. Exits 2 when an uncommitted plan sits at `status: done` but is
missing its `pr:` value, or leaves Validation boxes unticked with an empty
Notes section. The closeout protocol (plans/README.md) permits unticked boxes
- but only with the reason recorded in Notes; silence is what hollows the
record out.

Only uncommitted plans are checked, so a historical plan can never wedge the
session.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import re
import sys

from _common import (
    git_pending_paths,
    is_icm_project,
    parse_plan_frontmatter,
    project_dir,
    read_event,
)

UNTICKED_RE = re.compile(r"^\s*- \[ \]", re.MULTILINE)
"""Regex to find unticked Validation boxes in a plan."""


def section(text: str, name: str) -> str:
    """Get the body of `## <name>`.

    NOTE: Processes up to the next H2 or end of file.

    Args:
        text: The plan document text.
        name: The section name, e.g. "Validation" or "Notes".

    Returns:
        The section body, or "" if the section is not found.
    """
    match = re.search(
        rf"^## {re.escape(name)}\s*$(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def main() -> int:
    """Main entry point for the gate."""
    event = read_event()
    if event.get("stop_hook_active"):
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    failures = []
    for _status, path in git_pending_paths(root, "plans"):
        if (
            not path.endswith(".md")
            or path == "plans/README.md"
            or path.count("/") != 1
        ):
            continue
        try:
            text = (root / path).read_text(encoding="utf-8")
        # ValueError included (issues #8, #17): it covers UnicodeDecodeError
        # for a non-UTF-8 plan and the embedded-NUL path that only raises
        # inside read_text - without it one bad plan aborted the loop and
        # stopped every other pending plan being judged.
        except (OSError, ValueError):
            continue
        meta = parse_plan_frontmatter(text)
        if not meta or meta["status"] != "done":
            continue
        if not meta["pr"]:
            failures.append(f"{path}: status is done but pr: is empty")
        if UNTICKED_RE.search(section(text, "Validation")) and not section(
            text, "Notes"
        ):
            failures.append(
                f"{path}: unticked Validation boxes with an empty Notes "
                "section - record why each box stays unticked"
            )
    if not failures:
        return 0

    sys.stderr.write(
        f"Closeout incomplete: {'; '.join(failures)}. Check plans/README.md."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: a new spec cannot land without an owner (Invariant 1).

Event: Stop. Exits 2 when a spec arriving under `specs/` is named by neither
the `specs:` nor the `authors:` field of any plan's frontmatter. Ownership
comes in two forms and the invariant accepts either: `specs:` claims the plan
brings code into conformance, `authors:` claims the plan writes the spec
without changing behaviour. A spec-authoring plan correctly carries
`specs: []`, so reading `specs:` alone would block the one case
`plans/README.md` calls correct and common.

Coverage is computed from frontmatter only - never a whole-file grep, which is
the documented way this invariant silently dies (plan prose routinely names
specs it does not implement).

Arrival is what is checked, and arrival is a change of path: untracked,
staged-add, or renamed and copied into place. Editing a committed spec leaves
its path alone, so it stays with the ripple protocol in `specs/README.md`,
where blocking would punish typo fixes. A rename does move the path, and the
path is the key every plan's `specs:` and `authors:` field is written in, so
the destination is checked like any other new spec. Conflicted paths mid-merge
are not arrivals - `GIT_UNMERGED` in `_common.py` says why.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys

from _common import (
    GIT_UNMERGED,
    git_pending_paths,
    is_icm_project,
    iter_plans,
    parse_plan_frontmatter,
    plan_spec_paths,
    project_dir,
    read_event,
)

# `git status --porcelain` index-column codes that mean the path is arriving in
# this commit: ? untracked, A added, R renamed into place, C copied into place.
# Only the index column is tested, because the worktree column says what has
# happened to the file *since* it arrived and cannot un-arrive it - "AM" is the
# same arrival as "A ", "RM" the same as "R ". Testing the two columns as one
# string is exactly what let "AM" and "R " walk past this gate (issue #1).
#
# C is unreachable under stock git, which does no copy detection in `status`;
# it is listed so that `status.renames = copies` cannot silently reopen the
# hole in someone's checkout.
NEW_INDEX_CODES = frozenset("?ARC")

# The subset of the above that arrived from an existing path rather than from
# nothing. These get an extra sentence in the block message, because the fix is
# to edit a stale entry, not to add a second one.
RELOCATED_INDEX_CODES = frozenset("RC")


def is_arriving(status: str) -> bool:
    """Does this porcelain status code mean a spec is new at this path?

    NOTE: `git_pending_paths` already drops `GIT_UNMERGED`, so the first test
    is defence in depth - it keeps the predicate honest read on its own, and
    testable without a git repository. `status[:1]` rather than `status[0]`
    for the same reason: depending on another module's length guarantee for
    exception safety is the shape of coupling that produced issue #1.

    Args:
        status: The two-character `git status --porcelain` XY code.

    Returns:
        True when the path is untracked, staged-added, renamed or copied into
        place, and is not mid-merge.
    """
    return status not in GIT_UNMERGED and status[:1] in NEW_INDEX_CODES


def main() -> int:
    event = read_event()
    if event.get("stop_hook_active"):
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    arrivals = [
        (status, path)
        for status, path in git_pending_paths(root, "specs")
        if is_arriving(status)
        and path.endswith(".md")
        and path != "specs/README.md"
    ]
    if not arrivals:
        return 0
    covered: set[str] = set()
    for _path, text in iter_plans(root):
        meta = parse_plan_frontmatter(text)
        if meta:
            covered.update(plan_spec_paths(meta))
    uncovered = [
        (status, path) for status, path in arrivals if path not in covered
    ]
    if not uncovered:
        return 0
    message = (
        "New spec(s) with no owning plan: "
        + ", ".join(path for _status, path in uncovered)
        + ". Every spec is either implemented or named by a plan's frontmatter (Invariant 1, "
        "specs/README.md). If this plan brings code into conformance with it, add it to "
        "specs:; if this plan only writes it and behaviour is unchanged, add it to authors:. "
        "Never both, and never a spec the plan merely mentions."
    )
    relocated = [
        path
        for status, path in uncovered
        if status[:1] in RELOCATED_INDEX_CODES
    ]
    if relocated:
        # Reached when a spec was renamed and its owning plan still names the
        # old path. The generic advice above would have the author add a second
        # entry and leave the first dangling - which gate_plan_frontmatter.py
        # then reports as unresolvable - so name the case and ask for an edit.
        message += (
            " Renamed or copied into place: "
            + ", ".join(relocated)
            + ". Coverage is keyed on the path, so a rename moves the key: edit the owning "
            "plan's existing entry to the new path in this same commit, rather than adding "
            "a second one."
        )
    sys.stderr.write(message)
    return 2


if __name__ == "__main__":
    sys.exit(main())

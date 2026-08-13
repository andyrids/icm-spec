# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: a new spec cannot land without an owner (Invariant 1).

Event: Stop. Exits 2 when an uncommitted, previously untracked file under
`specs/` is named by neither the `specs:` nor the `authors:` field of any
plan's frontmatter. Ownership comes in two forms and the invariant accepts
either: `specs:` claims the plan brings code into conformance, `authors:`
claims the plan writes the spec without changing behaviour. A spec-authoring
plan correctly carries `specs: []`, so reading `specs:` alone would block the
one case `plans/README.md` calls correct and common.

Coverage is computed from frontmatter only - never a whole-file grep, which is
the documented way this invariant silently dies (plan prose routinely names
specs it does not implement).

Only untracked specs are checked: a committed spec has passed human review,
and a merely modified spec is handled by the ripple protocol in
`specs/README.md`, where blocking would punish typo fixes.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys

from _common import (
    git_pending_paths,
    is_icm_project,
    iter_plans,
    parse_plan_frontmatter,
    plan_spec_paths,
    project_dir,
    read_event,
)


def main() -> int:
    event = read_event()
    if event.get("stop_hook_active"):
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    new_specs = [
        path
        for status, path in git_pending_paths(root, "specs")
        if status.strip() in {"??", "A"}
        and path.endswith(".md")
        and path != "specs/README.md"
    ]
    if not new_specs:
        return 0
    covered: set[str] = set()
    for _path, text in iter_plans(root):
        meta = parse_plan_frontmatter(text)
        if meta:
            covered.update(plan_spec_paths(meta))
    uncovered = [spec for spec in new_specs if spec not in covered]
    if not uncovered:
        return 0
    sys.stderr.write(
        "New spec(s) with no owning plan: "
        + ", ".join(uncovered)
        + ". Every spec is either implemented or named by a plan's frontmatter (Invariant 1, "
        "specs/README.md). If this plan brings code into conformance with it, add it to "
        "specs:; if this plan only writes it and behaviour is unchanged, add it to authors:. "
        "Never both, and never a spec the plan merely mentions."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

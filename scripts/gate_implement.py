# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: `/icm:implement` requires an open plan.

Event: UserPromptExpansion. Blocks the command expanding (exit 2) when no
top-level plan is at `status: planned` or `status: in-progress` - stage 01
opens the plan at `planned` and stage 02 itself flips it to `in-progress`, so
both states count as an open plan.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys

from _common import (
    is_icm_project,
    iter_plans,
    parse_plan_frontmatter,
    project_dir,
    read_event,
)

OPEN_STATUSES = {"planned", "in-progress"}


def main() -> int:
    """Main entry point for the gate."""
    event = read_event()
    prompt = str(event.get("prompt", ""))
    if not prompt.lstrip().startswith("/icm:implement"):
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    for _path, text in iter_plans(root):
        meta = parse_plan_frontmatter(text)
        if meta and meta["status"] in OPEN_STATUSES:
            return 0
    sys.stderr.write(
        "No plan in plans/ with status planned or in-progress. Stage 02 implements an "
        "accepted plan - run /icm:specify first to produce the spec change, the plan and "
        "the techspec."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

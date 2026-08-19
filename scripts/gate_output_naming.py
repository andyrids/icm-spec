# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: stage output files follow the shared-slug naming convention.

Event: PreToolUse (Edit|Write). Denies a write into a stage `output/`
directory of a workspace in `OUTPUT_WORKSPACES` (currently `process-plan`)
unless the filename is `<slug>-<suffix>.md` with the suffix the stage owns
(01 -> spec, 02 -> code, 03 -> test, 04 -> docs), per
`ICM/_config/reference-standard-naming.md`. The slug correlates a run's
artifacts across all four stages, so a stray name breaks the handoff chain.
Workspaces whose contracts declare no stage-output artifacts (e.g.
`express-change`) fall outside this gate's authority, and like every gate
it no-ops entirely when the project has no `ICM/` tree.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import re
import sys

from _common import (
    SLUG_SUFFIX_BY_STAGE,
    emit,
    is_icm_project,
    project_dir,
    read_event,
    relative_posix,
    tool_input,
)

OUTPUT_RE = re.compile(r"^ICM/([^/]+)/stages/(\d{2})-[^/]+/output/(.+)$")
OUTPUT_WORKSPACES = frozenset({"process-plan"})
NAME_RE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)-(spec|code|test|docs)\.md$")


def main() -> int:
    """Main entry point for the gate script."""
    event = read_event()
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    file_path = str(tool_input(event).get("file_path", ""))
    if not file_path:
        return 0
    rel = relative_posix(file_path, root)
    if rel is None:
        return 0
    match = OUTPUT_RE.match(rel)
    if match is None:
        return 0
    workspace, stage, name = match.groups()
    if workspace not in OUTPUT_WORKSPACES:
        return 0
    if name == ".gitkeep":
        return 0
    expected = SLUG_SUFFIX_BY_STAGE.get(stage)
    name_match = NAME_RE.match(name)
    if expected and name_match and name_match.group(2) == expected:
        return 0
    emit(
        "PreToolUse",
        permissionDecision="deny",
        permissionDecisionReason=(
            f"{rel} breaks the stage output naming convention. Stage {stage} writes "
            f"<slug>-{expected or 'spec|code|test|docs'}.md, with the kebab-case slug shared "
            "by the plan and every other stage artifact - see "
            "ICM/_config/reference-standard-naming.md."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

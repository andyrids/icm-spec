# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: edits under specs/ surface for human review.

Event: PreToolUse (Edit|Write). Answers `permissionDecision: "ask"` for any
write into the top-level `specs/` tree - never a hard deny, because spec
amendment is legitimate stage-01 (re-entry) work; the human is the gate.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys

from _common import emit, is_icm_project, project_dir, read_event, relative_posix


def main() -> int:
    event = read_event()
    file_path = str(event.get("tool_input", {}).get("file_path", ""))
    if not file_path:
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    rel = relative_posix(file_path, root)
    if rel is None or not rel.startswith("specs/"):
        return 0
    emit(
        "PreToolUse",
        permissionDecision="ask",
        permissionDecisionReason=(
            f"{rel} declares permanent desired state. Spec changes belong to stage 01 - "
            "or to a re-entry into it when a later stage invalidates the spec. Approve if "
            "that is what this is."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

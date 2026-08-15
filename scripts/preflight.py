# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Preflight: announce the armed gates at the start of every ICM session.

Event: SessionStart (matcher: startup). Every gate runs through `uv`, and a
gate whose runtime is missing exits non-zero - which Claude Code treats as
non-blocking, so the pipeline runs unenforced. A hook cannot detect the
absence of its own runtime, so this one inverts the check: inside an ICM tree
it emits one line naming the plugin version and the gates armed. The line is
the positive signal; its absence in a scaffolded repository is the tell that
the hook runtime is broken.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import json
import sys
from pathlib import Path

from _common import emit, is_icm_project, project_dir, read_event

SCRIPTS = Path(__file__).resolve().parent


def plugin_version() -> str:
    """Read the version from the plugin manifest, or "unknown"."""
    manifest = SCRIPTS.parent / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    # UnicodeDecodeError included (issue #8): it is a ValueError raised by
    # `read_text`, not `json.loads`, so neither guard caught it - and the
    # banner is the positive signal, so it must degrade to "unknown", not
    # vanish.
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "unknown"
    return (
        str(data.get("version", "unknown"))
        if isinstance(data, dict)
        else "unknown"
    )


def main() -> int:
    """Main entry point for the preflight hook."""
    event = read_event()
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    # Counted from disk rather than hardcoded, so the banner cannot drift from
    # the inventory the way a prose count can.
    gates = len(list(SCRIPTS.glob("gate_*.py")))
    emit(
        "SessionStart",
        additionalContext=(
            f"icm {plugin_version()} preflight: ICM tree detected, "
            f"{gates} gates armed."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

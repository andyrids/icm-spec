# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate: `/icm:implement` requires every clarification resolved.

Event: UserPromptExpansion. Stage 01 marks unresolved decisions inline as
`[NEEDS CLARIFICATION: <question>]` in its techspec scratch. Blocks the
command expanding (exit 2) while any marker survives, naming the file and
each open question - implementing over an open question means guessing its
answer, which is how a spec and its code diverge inside a single run.

Reads the gitignored stage scratch directly: `git status` cannot see it, so
`git_pending_paths` cannot either. No stage 01 output at all is a pass - the
express pipeline writes none, and cleaned scratch must never block re-entry.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import re
import sys

from _common import is_icm_project, project_dir, read_event

MARKER = "[NEEDS CLARIFICATION"
QUESTION = re.compile(r"\[NEEDS CLARIFICATION[^\]]*\]")


def main() -> int:
    """Main entry point for the gate."""
    event = read_event()
    prompt = str(event.get("prompt", ""))
    if not prompt.lstrip().startswith("/icm:implement"):
        return 0
    root = project_dir(event)
    if not is_icm_project(root):
        return 0
    findings: list[str] = []
    for path in sorted(root.glob("ICM/*/stages/01-*/output/*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if MARKER not in text:
            continue
        rel = path.relative_to(root).as_posix()
        for question in QUESTION.findall(text) or [f"{MARKER}]"]:
            findings.append(f"  {rel}: {question}")
    if not findings:
        return 0
    sys.stderr.write(
        "Unresolved [NEEDS CLARIFICATION] markers in stage 01 output. Answer each "
        "question and edit the techspec - and the spec or plan, if the answer moves "
        "them - before implementing:\n" + "\n".join(findings)
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

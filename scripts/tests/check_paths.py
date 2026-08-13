"""Check that every static path a scaffolded ICM tree cites in prose resolves.

This is the test that would have caught the three defects `/icm:init` shipped
with: a workspace directory the skills addressed but the templates did not
create, a Layer 0 template the mapping table promised and no file backed, and
two toolchain references a stage contract named that were never written. Each
was a backtick-quoted path in prose that pointed at nothing, and nothing was
looking.

With no argument it simulates a scaffold from `skills/init/templates/` into a
temporary directory and checks that - so it runs in CI with no fixture. Given
a path it checks that tree instead, which is how to audit a real project.

Fenced blocks are stripped before scanning: tree diagrams and template
examples name paths illustratively rather than referentially. A reference
resolves if it exists relative to the tree root or to the citing file.

Run: python scripts/tests/check_paths.py [path]

License:
    SPDX-License-Identifier: Apache-2.0
"""

import re
import shutil
import sys
import tempfile
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent.parent / "skills" / "init" / "templates"

FENCE = re.compile(r"^```.*?^```", re.S | re.M)
TOKEN = re.compile(r"`([^`\n]+)`")
# A token holding any of these is a pattern, a placeholder or a URL, not a path.
SKIP_CHARS = ("<", ">", "*", "[", "$", " ")

# Every table in the naming standard is an illustrative example - the file
# teaches filename patterns, so its `example` columns name files on purpose.
EXCLUDE_FILES = {"ICM/_config/reference-standard-naming.md"}

# Paths deliberately absent from a fresh scaffold. An entry here is a claim
# that the citation is correct and the file's absence is by design - so each
# carries the reason, and an unexplained addition is the smell.
NOT_SCAFFOLDED = {
    "specs/principles.md": (
        "promoted into on the first project-wide principle - scaffolding it "
        "empty would ship a constitution with nothing in it"
    ),
    "README.md": "the project's own README, which ICM neither writes nor owns",
}


def scaffold(dest: Path) -> None:
    """Copy the init templates into `dest` under their destination names.

    NOTE: Mirrors the mapping table in `skills/init/SKILL.md`. Only `gitignore`
    is renamed; everything else lands at its template path.

    Args:
        dest: The directory to scaffold into.
    """
    shutil.copytree(TEMPLATES, dest, dirs_exist_ok=True)
    (dest / "gitignore").rename(dest / ".gitignore")


def unresolved(root: Path) -> list[tuple[str, str]]:
    """Find every cited path in `root` that does not resolve.

    Args:
        root: The tree root to scan.

    Returns:
        `(citing file, path)` pairs, sorted, one per unresolved reference.
    """
    bad = []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if rel in EXCLUDE_FILES:
            continue
        text = FENCE.sub("", md.read_text(encoding="utf-8"))
        for raw in TOKEN.findall(text):
            token = raw.strip().rstrip("/")
            if not token.endswith(".md") or token.startswith("http"):
                continue
            if any(char in token for char in SKIP_CHARS):
                continue
            if token in NOT_SCAFFOLDED:
                continue
            if not ((root / token).exists() or (md.parent / token).exists()):
                bad.append((rel, token))
    return bad


def main() -> int:
    """Main entry point for the check."""
    if len(sys.argv) > 1:
        return report(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve() / "scaffold"
        scaffold(root)
        return report(root)


def report(root: Path) -> int:
    """Print the verdict for one tree and return its exit code."""
    if not root.is_dir():
        print(f"  no such tree: {root}")
        return 1
    total = sum(1 for _ in root.rglob("*.md"))
    bad = unresolved(root)
    for where, token in bad:
        print(f"  MISSING   {token:<26} cited by {where}")
    for token, reason in sorted(NOT_SCAFFOLDED.items()):
        print(f"  by design {token:<26} {reason}")
    print(f"\n{total} documents scanned, {len(bad)} unresolved path references")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

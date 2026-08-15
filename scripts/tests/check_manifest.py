# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Check that the plugin version agrees everywhere it is stated.

Claude Code resolves a plugin's version from `plugin.json` first, then the
marketplace entry, then the source commit SHA - and an update ships only
when the resolved string changes. Declaring the version in the first two
places at once is the documented failure mode: `plugin.json` wins silently,
so a stale manifest can mask a marketplace bump and the release reaches
nobody. This repository's arrangement is therefore one authoritative field,
`plugin.json`, with the human-facing statements - the CHANGELOG top release
heading - required to agree with it.

Four assertions: 

1. `plugin.json` declares a `version`
2. The marketplace entry for `icm` does not
3. The CHANGELOG topmost release heading matches unless `[unreleased]`.

Run: uv run --no-project --script scripts/tests/check_manifest.py

License:
    SPDX-License-Identifier: Apache-2.0
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"

HEADING = re.compile(r"^## \[([^\]]+)\]", re.M)


def line_of(text: str, offset: int) -> int:
    """Return the 1-based line number of character `offset` in `text`."""
    return text.count("\n", 0, offset) + 1


def main() -> int:
    """Main entry point for the check."""
    bad: list[tuple[str, str]] = []

    version = json.loads(PLUGIN.read_text(encoding="utf-8")).get("version")
    if not version:
        bad.append(
            (
                ".claude-plugin/plugin.json",
                "declares no version - the authoritative field is empty",
            )
        )

    catalog = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entry = next(
        (p for p in catalog.get("plugins", []) if p.get("name") == "icm"), None
    )
    if entry is None:
        bad.append(
            (".claude-plugin/marketplace.json", "has no entry named icm")
        )
    elif "version" in entry:
        bad.append(
            (
                ".claude-plugin/marketplace.json",
                f"entry for icm declares version {entry['version']} - plugin.json masks it silently; remove it",
            )
        )

    changelog = CHANGELOG.read_text(encoding="utf-8")
    heading = HEADING.search(changelog)
    if heading is None:
        bad.append(("CHANGELOG.md", "has no release heading"))
    elif version and heading.group(1) not in ("unreleased", version):
        bad.append(
            (
                f"CHANGELOG.md:{line_of(changelog, heading.start())}",
                f"top release heading is [{heading.group(1)}], plugin.json says {version}",
            )
        )

    for where, why in bad:
        print(f"  DRIFT  {where:<15} {why}")
    print(f"\n4 version statements checked, {len(bad)} in disagreement")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

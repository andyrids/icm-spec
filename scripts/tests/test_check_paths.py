"""Companion tests for `check_paths.py`; the program is unchanged.

NOTE: `check_paths.main()` is never called in-process - it reads
`sys.argv[1]`, which collides with unittest's own argv. The functions
are tested directly and the optional-path CLI contract is pinned with
one real subprocess.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

from . import check_paths
from .support import TempDirCase


class ScaffoldTests(TempDirCase):
    scaffold_icm = False

    def test_scaffold_renames_gitignore(self) -> None:
        # Only `gitignore` is renamed; everything else lands at its
        # template path - mirroring the mapping table in
        # skills/init/SKILL.md.
        dest = self.root / "scaffold"
        check_paths.scaffold(dest)
        self.assertTrue((dest / ".gitignore").is_file())
        self.assertFalse((dest / "gitignore").exists())
        self.assertTrue((dest / "AGENTS.md").is_file())

    def test_a_fresh_scaffold_has_no_unresolved_paths(self) -> None:
        # The CI default: what `/icm:init` ships must cite only paths it
        # also creates (or allowlists with a reason).
        dest = self.root / "scaffold"
        check_paths.scaffold(dest)
        self.assertEqual(check_paths.unresolved(dest), [])


class UnresolvedTests(TempDirCase):
    scaffold_icm = False

    def test_reports_a_citation_that_resolves_nowhere(self) -> None:
        (self.root / "a.md").write_text(
            "See `missing.md` for details.\n", encoding="utf-8"
        )
        self.assertEqual(
            check_paths.unresolved(self.root), [("a.md", "missing.md")]
        )

    def test_resolves_against_root_and_citing_file(self) -> None:
        # A reference resolves if it exists relative to the tree root or
        # to the citing file.
        docs = self.root / "docs"
        docs.mkdir()
        (self.root / "top.md").write_text("# top\n", encoding="utf-8")
        (docs / "sibling.md").write_text("# sib\n", encoding="utf-8")
        (docs / "a.md").write_text(
            "See `top.md` and `sibling.md`.\n", encoding="utf-8"
        )
        self.assertEqual(check_paths.unresolved(self.root), [])

    def test_fenced_blocks_and_patterns_are_skipped(self) -> None:
        # Tree diagrams and template examples name paths illustratively
        # rather than referentially; placeholder tokens are patterns.
        (self.root / "a.md").write_text(
            "```\n`inside-fence.md`\n```\n"
            "A `<placeholder>.md` and `specs/*.md` pattern.\n"
            "A `https://example.com/x.md` URL.\n",
            encoding="utf-8",
        )
        self.assertEqual(check_paths.unresolved(self.root), [])

    def test_allowlisted_absences_are_by_design(self) -> None:
        (self.root / "a.md").write_text(
            "Promote into `specs/principles.md`.\n", encoding="utf-8"
        )
        self.assertEqual(check_paths.unresolved(self.root), [])


class ReportTests(TempDirCase):
    scaffold_icm = False

    def _report(self, root: Path) -> tuple[int, str]:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = check_paths.report(root)
        return rc, out.getvalue()

    def test_missing_tree_fails(self) -> None:
        rc, out = self._report(self.root / "nowhere")
        self.assertEqual(rc, 1)
        self.assertIn("no such tree", out)

    def test_clean_tree_passes_and_names_the_allowlist(self) -> None:
        (self.root / "a.md").write_text("# a\n", encoding="utf-8")
        rc, out = self._report(self.root)
        self.assertEqual(rc, 0)
        self.assertIn("0 unresolved path references", out)
        self.assertIn("by design", out)

    def test_bad_tree_fails_and_names_the_citation(self) -> None:
        (self.root / "a.md").write_text("`missing.md`\n", encoding="utf-8")
        rc, out = self._report(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("MISSING", out)
        self.assertIn("missing.md", out)


class CliContractTests(TempDirCase):
    scaffold_icm = False

    def test_optional_path_argument_audits_that_tree(self) -> None:
        (self.root / "a.md").write_text("`missing.md`\n", encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(check_paths.__file__)),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("MISSING", proc.stdout)


if __name__ == "__main__":
    unittest.main()

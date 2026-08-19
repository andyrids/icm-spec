"""Layer B+git: the porcelain status matrix behind issues #1 and #6.

Each row builds a fixture, asserts the status code git actually
produced, then asserts the verdict. The fixture-shape assertion comes
first because a fixture that degrades quietly - a rename landing as
D+A, an edit git calls racily clean - turns a regression row green for
the wrong reason. Separate methods rather than `subTest` because each
row's *construction procedure* differs (mv vs merge vs plain write) and
carries load-bearing prose.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest
from pathlib import Path

import gate_closeout
import gate_spec_coverage

from .support import (
    TempDirCase,
    call_gate_main,
    case_repo,
    git,
    git_commit_all,
    porcelain,
    write_plan,
    write_spec,
)


class SpecCoveragePorcelainMatrixTests(TempDirCase):
    scaffold_icm = False  # each row builds its own repo via case_repo
    scaffold_git = False

    def _verdict(self, repo: Path) -> tuple[int, str, str]:
        return call_gate_main(
            gate_spec_coverage,
            {"cwd": str(repo), "stop_hook_active": False},
        )

    def test_untracked_blocks(self) -> None:
        """Check the gate blocks on an untracked spec."""

        # ?? - restated from the six-step flow so the matrix reads as one.
        repo = case_repo(self.root, "untracked")
        write_spec(repo, "orphan")
        self.assertEqual(
            porcelain(repo, "specs"), ["?? specs/commands/orphan.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("orphan.md", err)

    def test_staged_blocks(self) -> None:
        """Check the gate blocks on a staged spec."""

        repo = case_repo(self.root, "staged")
        write_spec(repo, "staged")
        git(repo, "add", "-A")
        self.assertEqual(
            porcelain(repo, "specs"), ["A  specs/commands/staged.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("staged.md", err)

    def test_staged_then_edited_blocks(self) -> None:
        """Check the gate blocks on a staged spec that is then edited."""

        repo = case_repo(self.root, "staged-then-edited")
        write_spec(repo, "edited", "# spec")
        git(repo, "add", "-A")
        write_spec(repo, "edited", "# spec, amended after staging")
        self.assertEqual(
            porcelain(repo, "specs"), ["AM specs/commands/edited.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("edited.md", err)

    def test_renamed_blocks(self) -> None:
        """Check the gate blocks on a renamed spec."""

        repo = case_repo(self.root, "renamed")
        write_spec(repo, "old")
        git_commit_all(repo)
        git(repo, "mv", "specs/commands/old.md", "specs/commands/new.md")
        self.assertEqual(
            porcelain(repo, "specs"),
            ["R  specs/commands/old.md -> specs/commands/new.md"],
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        # Pins defect C independently of B: fails a partial fix that
        # widens the status set without splitting the `old -> new`
        # payload.
        self.assertIn("specs/commands/new.md", err)
        self.assertNotIn(" -> ", err)

    def test_renamed_past_covered_spec_blocks(self) -> None:
        """Check the gate blocks on a renamed spec that is already covered."""

        repo = case_repo(self.root, "renamed-covered")
        write_spec(repo, "old")
        write_plan(repo, "owner", specs="\n  - specs/commands/old.md")
        git_commit_all(repo)
        git(repo, "mv", "specs/commands/old.md", "specs/commands/new.md")
        self.assertEqual(
            porcelain(repo, "specs"),
            ["R  specs/commands/old.md -> specs/commands/new.md"],
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("specs/commands/new.md", err)
        self.assertIn("edit the owning plan's existing entry", err)

    def test_inbound_rename_blocks(self) -> None:
        """Check the gate blocks on an inbound rename."""

        repo = case_repo(self.root, "renamed-inbound")
        (repo / "docs").mkdir()
        (repo / "docs" / "a.md").write_text("# doc\n", encoding="utf-8")
        (repo / "specs" / "commands").mkdir(parents=True)
        git_commit_all(repo)
        git(repo, "mv", "docs/a.md", "specs/commands/a.md")
        self.assertEqual(
            porcelain(repo, "specs"), ["A  specs/commands/a.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("specs/commands/a.md", err)
        self.assertNotIn(" -> ", err)

    def test_modified_never_blocks(self) -> None:
        """Check the gate does not block on a modified spec."""

        repo = case_repo(self.root, "modified")
        write_spec(repo, "settled")
        git_commit_all(repo)
        write_spec(repo, "settled", "# spec, revised after review")
        self.assertEqual(
            porcelain(repo, "specs"), [" M specs/commands/settled.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_staged_modification_never_blocks(self) -> None:
        """Check the gate does not block on a staged modification."""

        repo = case_repo(self.root, "modified-staged")
        write_spec(repo, "settled")
        git_commit_all(repo)
        write_spec(repo, "settled", "# spec, revised after review")
        git(repo, "add", "-A")
        self.assertEqual(
            porcelain(repo, "specs"), ["M  specs/commands/settled.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_staged_then_edited_modification_never_blocks(self) -> None:
        """Check the gate does not block on an edited, staged modification."""

        repo = case_repo(self.root, "modified-twice")
        write_spec(repo, "settled")
        git_commit_all(repo)
        write_spec(repo, "settled", "# spec, revised after review")
        git(repo, "add", "-A")
        write_spec(repo, "settled", "# spec, revised twice over")
        self.assertEqual(
            porcelain(repo, "specs"), ["MM specs/commands/settled.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_conflicted_never_blocks(self) -> None:
        """Check the gate does not block on a conflicted spec."""

        repo = case_repo(self.root, "conflicted")
        (repo / "specs").mkdir(parents=True, exist_ok=True)
        (repo / "specs" / "README.md").write_text(
            "# Specs\n", encoding="utf-8"
        )
        git_commit_all(repo)
        git(repo, "checkout", "-q", "-b", "other")
        write_spec(repo, "clash", "# spec, theirs")
        git_commit_all(repo)
        git(repo, "checkout", "-q", "-")
        write_spec(repo, "clash", "# spec, ours")
        git_commit_all(repo)
        git(repo, "merge", "--no-edit", "other", check=False)
        lines = porcelain(repo, "specs")
        self.assertTrue(
            any(line.startswith("AA ") for line in lines),
            f"lines={lines}",
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")


class ClosePlanRenameTests(TempDirCase):
    """check a moved plan is judged at its destination."""

    scaffold_icm = False  # each row builds its own repo via case_repo
    scaffold_git = False

    def _verdict(self, repo: Path) -> tuple[int, str, str]:
        return call_gate_main(
            gate_closeout, {"cwd": str(repo), "stop_hook_active": False}
        )

    def test_control_untracked_done_plan_blocks(self) -> None:
        """Check the gate blocks on an untracked done plan."""

        repo = case_repo(self.root, "control")
        write_plan(repo, "renamed-plan", status="done", pr="")
        self.assertEqual(
            porcelain(repo, "plans"), ["?? plans/renamed-plan.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("pr:", err)

    def test_renamed_done_plan_blocks(self) -> None:
        """Check the gate blocks on a renamed done plan."""

        repo = case_repo(self.root, "renamed")
        write_plan(repo, "old-plan", status="in-progress", pr="")
        git_commit_all(repo)
        git(repo, "mv", "plans/old-plan.md", "plans/renamed-plan.md")
        write_plan(repo, "renamed-plan", status="done", pr="")
        # Staged, so the fixture reaches "R " rather than "RM".
        git(repo, "add", "-A")
        self.assertEqual(
            porcelain(repo, "plans"),
            ["R  plans/old-plan.md -> plans/renamed-plan.md"],
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("plans/renamed-plan.md", err)
        # Vacuous while stderr is empty; it exists to catch a fix that
        # splits the `old -> new` payload on the wrong side.
        self.assertNotIn(" -> ", err)
        self.assertNotIn("old-plan", err)


class NonAsciiPathTests(TempDirCase):
    """A non-ASCII path must reach the gates as the file on disk."""

    scaffold_icm = False  # each row builds its own repo via case_repo
    scaffold_git = False

    # What newline porcelain makes of `café` under the default
    # `core.quotepath=true`: C-quoted, é octal-escaped byte by byte.
    QUOTED_SPEC = '?? "specs/commands/caf\\303\\251.md"'

    def _coverage(self, repo: Path) -> tuple[int, str, str]:
        return call_gate_main(
            gate_spec_coverage,
            {"cwd": str(repo), "stop_hook_active": False},
        )

    def _closeout(self, repo: Path) -> tuple[int, str, str]:
        return call_gate_main(
            gate_closeout, {"cwd": str(repo), "stop_hook_active": False}
        )

    def test_uncovered_nonascii_spec_blocks_naming_the_real_path(
        self,
    ) -> None:
        """Check the gate blocks uncovered specs with incorrect names."""

        repo = case_repo(self.root, "nonascii-uncovered")
        write_spec(repo, "café")
        self.assertEqual(porcelain(repo, "specs"), [self.QUOTED_SPEC])
        rc, _out, err = self._coverage(repo)
        self.assertEqual(rc, 2)
        # The block must name a path the author can act on - the file on
        # disk, not the phantom `/303/` directories the old parse built.
        self.assertIn("specs/commands/café.md", err)
        self.assertNotIn("/303/", err)

    def test_covered_nonascii_spec_passes(self) -> None:
        """Check the gate passes covered specs with incorrect names."""

        repo = case_repo(self.root, "nonascii-covered")
        write_spec(repo, "café")
        write_plan(
            repo, "owner", authors="\n  - specs/commands/café.md"
        )
        self.assertEqual(porcelain(repo, "specs"), [self.QUOTED_SPEC])
        rc, _out, err = self._coverage(repo)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_done_nonascii_plan_with_empty_pr_blocks(self) -> None:
        """Check gate blocks done plans with incorrect names & empty PR."""

        # Claim B of #6: the mangled path raised FileNotFoundError inside
        # gate_closeout's `except OSError`, so a half-closed plan slid
        # through. With the real path the plan opens and is judged.
        repo = case_repo(self.root, "nonascii-closeout")
        write_plan(repo, "café-plan", status="done", pr="")
        self.assertEqual(
            porcelain(repo, "plans"),
            ['?? "plans/caf\\303\\251-plan.md"'],
        )
        rc, _out, err = self._closeout(repo)
        self.assertEqual(rc, 2)
        self.assertIn("plans/café-plan.md", err)
        self.assertIn("pr:", err)


if __name__ == "__main__":
    unittest.main()

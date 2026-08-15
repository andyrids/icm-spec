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
        # Deliberately a different length after staging: an
        # identical-size rewrite inside one timestamp is the one shape
        # git can call racily clean.
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
        # Decision 3 made executable: coverage is keyed on the path, so
        # a rename moves the key and the stale specs: entry must be
        # edited, not doubled.
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
        # A guard, not a regression: pathspec limiting splits the
        # inbound rename, so the gate sees a bare "A " at the
        # destination (measured against git 2.55.0) and even the pre-fix
        # code blocked it. The row pins that a fix keyed on rename
        # handling does not lose the case where git reports no rename at
        # all.
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
        # The ripple carve-out: a merely modified committed spec never
        # blocks, whatever mix of index and worktree the modification
        # sits in.
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
        # Decision 2 made a tested decision rather than a comment: a
        # conflicted path mid-merge is not an arrival, and proves the fix
        # does not buy its blocking rows by blocking everything. Never
        # name the first branch - `init.defaultBranch` varies - so return
        # with `checkout -`.
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
    """A `git mv`d plan must still be judged at its destination (#1)."""

    scaffold_icm = False  # each row builds its own repo via case_repo
    scaffold_git = False

    def _verdict(self, repo: Path) -> tuple[int, str, str]:
        return call_gate_main(
            gate_closeout, {"cwd": str(repo), "stop_hook_active": False}
        )

    def test_control_untracked_done_plan_blocks(self) -> None:
        # Control: the same plan content blocks when it arrives
        # untracked, so the rename row below can differ in verdict for
        # one reason only - the parse.
        repo = case_repo(self.root, "control")
        write_plan(repo, "renamed-plan", status="done", pr="")
        self.assertEqual(
            porcelain(repo, "plans"), ["?? plans/renamed-plan.md"]
        )
        rc, _out, err = self._verdict(repo)
        self.assertEqual(rc, 2)
        self.assertIn("pr:", err)

    def test_renamed_done_plan_blocks(self) -> None:
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
    """A non-ASCII path must reach the gates as the file on disk (#6).

    Newline porcelain C-quotes any non-plain path, and the old parse read
    the surviving octal escapes as directories: `specs/café.md` became
    `specs/caf/303/251.md`, deadlocking the coverage gate and letting the
    closeout gate fail open on a FileNotFoundError. Each row asserts the
    quoted line via the `porcelain` oracle FIRST - proof that git still
    quotes and the gate stopped caring, not that the fixture stopped
    triggering. Filenames carrying `"`, backslash or control characters
    cannot exist on NTFS, so those trigger classes live only in the mocked
    rows of `test_common.py`.
    """

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
        # Claim A of #6 made executable: before the fix no frontmatter
        # value could satisfy the gate, because the plan names the real
        # path and the gate compared against the mangled one.
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

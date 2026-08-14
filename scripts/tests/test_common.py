"""Layer A: every public function in `_common.py`, no subprocess.

The module every gate's verdict flows through previously had no direct
test at all - each function was exercised only as a side effect of some
gate blocking. `git_pending_paths` is tested against a mocked
`subprocess.run` here; the porcelain matrix proves git itself produces
these lines.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import _common

from .support import TempDirCase, make_icm_tree


def _status_proc(stdout: str, returncode: int = 0) -> mock.Mock:
    """A canned `git status` result for patching `_common.subprocess.run`."""
    return mock.Mock(returncode=returncode, stdout=stdout)


class ReadEventTests(unittest.TestCase):
    def test_parses_a_json_object(self) -> None:
        event = {"cwd": "/x", "stop_hook_active": False}
        with mock.patch("sys.stdin", io.StringIO(json.dumps(event))):
            self.assertEqual(_common.read_event(), event)

    def test_invalid_json_degrades_to_empty(self) -> None:
        # Exit 2 is reserved for hard blocks; a malformed event must never
        # crash a gate, so the parse failure degrades to {}.
        with mock.patch("sys.stdin", io.StringIO("not json")):
            self.assertEqual(_common.read_event(), {})

    def test_non_dict_json_degrades_to_empty(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("[1, 2]")):
            self.assertEqual(_common.read_event(), {})


class ProjectDirTests(unittest.TestCase):
    def test_resolves_cwd_from_the_event(self) -> None:
        self.assertEqual(
            _common.project_dir({"cwd": "."}), Path(".").resolve()
        )

    def test_missing_cwd_falls_back_to_dot(self) -> None:
        self.assertEqual(_common.project_dir({}), Path(".").resolve())


class IsIcmProjectTests(TempDirCase):
    scaffold_icm = False

    def test_false_without_the_marker(self) -> None:
        self.assertFalse(_common.is_icm_project(self.root))

    def test_true_once_icm_init_has_run(self) -> None:
        make_icm_tree(self.root)
        self.assertTrue(_common.is_icm_project(self.root))


class RelativePosixTests(TempDirCase):
    scaffold_icm = False

    def test_inside_the_root_is_forward_slashed(self) -> None:
        inside = self.root / "specs" / "commands" / "find.md"
        self.assertEqual(
            _common.relative_posix(str(inside), self.root),
            "specs/commands/find.md",
        )

    def test_outside_the_root_is_none(self) -> None:
        outside = self.root.parent / "elsewhere.md"
        self.assertIsNone(_common.relative_posix(str(outside), self.root))


class FrontmatterLinesTests(unittest.TestCase):
    def test_returns_the_block_lines(self) -> None:
        text = "---\nstatus: done\npr: 7\n---\n\n# Plan\n"
        self.assertEqual(
            _common.frontmatter_lines(text), ["status: done", "pr: 7"]
        )

    def test_no_opening_fence_is_none(self) -> None:
        self.assertIsNone(_common.frontmatter_lines("# Plan\n"))

    def test_unterminated_fence_is_none(self) -> None:
        self.assertIsNone(_common.frontmatter_lines("---\nstatus: done\n"))


class ParsePlanFrontmatterTests(unittest.TestCase):
    def test_scalars_lists_and_hierarchy_keys(self) -> None:
        meta = _common.parse_plan_frontmatter(
            "---\n"
            "context-hierarchy: Layer 4\n"
            "context-hierarchy-role: Working artifact\n"
            "immutable: false\n"
            "status: in-progress  # mid-flight\n"
            "specs:\n"
            "  - specs/commands/a.md\n"
            "  - specs/commands/b.md  # trailing comment\n"
            "authors: []\n"
            "pr: 12\n"
            "---\n\n# Plan\n"
        )
        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertEqual(meta["status"], "in-progress")
        self.assertEqual(meta["pr"], "12")
        self.assertEqual(
            meta["specs"], ["specs/commands/a.md", "specs/commands/b.md"]
        )
        self.assertEqual(meta["authors"], [])
        self.assertEqual(meta["context-hierarchy"], "Layer 4")
        self.assertEqual(
            meta["context-hierarchy-role"], "Working artifact"
        )
        self.assertEqual(meta["immutable"], "false")

    def test_inline_list_syntax(self) -> None:
        meta = _common.parse_plan_frontmatter(
            "---\nspecs: [specs/a.md, specs/b.md]\n---\n"
        )
        assert meta is not None
        self.assertEqual(meta["specs"], ["specs/a.md", "specs/b.md"])

    def test_empty_values_read_as_none(self) -> None:
        meta = _common.parse_plan_frontmatter("---\nstatus:\npr:\n---\n")
        assert meta is not None
        self.assertIsNone(meta["status"])
        self.assertIsNone(meta["pr"])

    def test_no_frontmatter_is_none(self) -> None:
        self.assertIsNone(_common.parse_plan_frontmatter("# Plan\n"))


class PlanSpecPathsTests(unittest.TestCase):
    def test_unions_both_fields_and_normalises_backslashes(self) -> None:
        # `specs` and `authors` answer different questions, but Invariant 1
        # asks only whether some plan owns the spec at all - either answer
        # means yes, hence the union.
        meta = {
            "specs": ["specs/commands/a.md", "specs\\commands\\b.md"],
            "authors": ["specs/behaviors/c.md"],
        }
        self.assertEqual(
            _common.plan_spec_paths(meta),
            {
                "specs/commands/a.md",
                "specs/commands/b.md",
                "specs/behaviors/c.md",
            },
        )


class IterPlansTests(TempDirCase):
    scaffold_icm = False

    def test_yields_sorted_plans_without_readme(self) -> None:
        plans = self.root / "plans"
        plans.mkdir()
        (plans / "b.md").write_text("# b", encoding="utf-8")
        (plans / "a.md").write_text("# a", encoding="utf-8")
        (plans / "README.md").write_text("# Plans", encoding="utf-8")
        found = list(_common.iter_plans(self.root))
        self.assertEqual(
            [path.name for path, _text in found], ["a.md", "b.md"]
        )
        self.assertEqual(found[0][1], "# a")

    def test_missing_plans_directory_yields_nothing(self) -> None:
        self.assertEqual(list(_common.iter_plans(self.root)), [])


class GitPendingPathsTests(unittest.TestCase):
    """Parsing contract only - real git behaviour lives in the matrix."""

    def _pending(self, stdout: str) -> list[tuple[str, str]]:
        with mock.patch(
            "_common.subprocess.run",
            return_value=_status_proc(stdout),
        ):
            return _common.git_pending_paths(Path("."), "specs")

    def test_status_column_is_positional(self) -> None:
        # The raw two-character column, spaces preserved: callers test
        # `status[0]` or `status[1]` and never `status.strip()`, which
        # collapses "A " and "AM" onto different strings (issue #1).
        rows = [
            ("?? specs/a.md", [("??", "specs/a.md")]),
            ("A  specs/a.md", [("A ", "specs/a.md")]),
            ("AM specs/a.md", [("AM", "specs/a.md")]),
            (" M specs/a.md", [(" M", "specs/a.md")]),
        ]
        for stdout, expected in rows:
            with self.subTest(stdout=stdout):
                self.assertEqual(self._pending(stdout), expected)

    def test_rename_returns_the_destination_only(self) -> None:
        # The destination is the only side a gate can open. Bound to the
        # LAST separator: porcelain v1 is ambiguous when a path itself
        # contains " -> ".
        self.assertEqual(
            self._pending("R  specs/old.md -> specs/new.md"),
            [("R ", "specs/new.md")],
        )
        self.assertEqual(
            self._pending("R  specs/a -> b.md -> specs/c.md"),
            [("R ", "specs/c.md")],
        )

    def test_arrow_in_an_ordinary_filename_is_left_alone(self) -> None:
        # The cut is anchored on the status column, so an arrow inside a
        # non-rename path never splits.
        self.assertEqual(
            self._pending("?? specs/a -> b.md"),
            [("??", "specs/a -> b.md")],
        )

    def test_unmerged_and_deleted_entries_are_dropped(self) -> None:
        # Nothing there to hold to a contract: an unmerged entry is a
        # merge in motion, and a "D" in either column means no file on
        # disk at that path.
        for line in ["AA specs/a.md", "UU specs/a.md", " D specs/a.md",
                     "D  specs/a.md"]:
            with self.subTest(line=line):
                self.assertEqual(self._pending(line), [])

    def test_quoted_paths_are_unquoted(self) -> None:
        self.assertEqual(
            self._pending('?? "specs/a.md"'), [("??", "specs/a.md")]
        )

    def test_short_lines_are_skipped(self) -> None:
        self.assertEqual(self._pending("??\n"), [])

    def test_git_failure_degrades_to_empty(self) -> None:
        # No repository means no verdict rather than a crash.
        with mock.patch(
            "_common.subprocess.run",
            return_value=_status_proc("fatal", returncode=128),
        ):
            self.assertEqual(
                _common.git_pending_paths(Path("."), "specs"), []
            )
        with mock.patch(
            "_common.subprocess.run", side_effect=OSError("no git")
        ):
            self.assertEqual(
                _common.git_pending_paths(Path("."), "specs"), []
            )
        with mock.patch(
            "_common.subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 15),
        ):
            self.assertEqual(
                _common.git_pending_paths(Path("."), "specs"), []
            )


class EmitTests(unittest.TestCase):
    def test_writes_hook_specific_output_json(self) -> None:
        buffer = io.StringIO()
        with mock.patch("sys.stdout", buffer):
            _common.emit("PreToolUse", permissionDecision="ask")
        self.assertEqual(
            json.loads(buffer.getvalue()),
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                }
            },
        )


if __name__ == "__main__":
    unittest.main()

"""Layer A: every public function in `_common.py`, no subprocess.

The module every gate's verdict flows through previously had no direct
test at all - each function was exercised only as a side effect of some
gate blocking. `git_pending_paths` is tested against a mocked
`subprocess.run` here; the porcelain matrix proves against real git that
the fixtures are shaped like the records it emits.

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


def _status_proc(stdout: bytes, returncode: int = 0) -> mock.Mock:
    """A canned `git status` result for patching `_common.subprocess.run`.

    NOTE: `stdout` is bytes, as `subprocess.run` returns without `text=True`:
    production decodes the `-z` NUL records by hand (issue #6), so a str here
    would test a decode path that no longer exists.
    """
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
    """Parsing contract only - real git behaviour lives in the matrix.

    Fixtures are the NUL-terminated records of `git status --porcelain -z`
    (issue #6): `XY <path>\\0`, with a rename's origin as its own trailing
    field. The characters `-z` exists for - non-ASCII, `"`, backslash -
    cannot be created on NTFS, so the mocked bytes here are the only place
    those trigger classes are testable; the matrix covers what real git on
    this filesystem can produce.
    """

    def _pending(self, stdout: bytes) -> list[tuple[str, str]]:
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
            (b"?? specs/a.md\x00", [("??", "specs/a.md")]),
            (b"A  specs/a.md\x00", [("A ", "specs/a.md")]),
            (b"AM specs/a.md\x00", [("AM", "specs/a.md")]),
            (b" M specs/a.md\x00", [(" M", "specs/a.md")]),
        ]
        for stdout, expected in rows:
            with self.subTest(stdout=stdout):
                self.assertEqual(self._pending(stdout), expected)

    def test_rename_returns_the_destination_only(self) -> None:
        # Under `-z` the field order is reversed - destination record first,
        # origin as the next NUL field - and the arrow is gone, so a path
        # containing " -> " is no longer ambiguous (it was under v1 newline
        # output, which needed an rsplit bound to the last separator).
        self.assertEqual(
            self._pending(b"R  specs/new.md\x00specs/old.md\x00"),
            [("R ", "specs/new.md")],
        )
        self.assertEqual(
            self._pending(b"R  specs/a -> b.md\x00specs/c.md\x00"),
            [("R ", "specs/a -> b.md")],
        )

    def test_rename_consumes_the_origin_field(self) -> None:
        # One tuple exactly: the origin field is discarded, never misread
        # as a second record - the destination is the only side a gate can
        # open.
        self.assertEqual(
            self._pending(
                b"R  specs/new.md\x00specs/old.md\x00?? specs/b.md\x00"
            ),
            [("R ", "specs/new.md"), ("??", "specs/b.md")],
        )

    def test_dropped_rename_does_not_desync_the_stream(self) -> None:
        # The ordering hazard in the parse loop: "RD" is dropped by the
        # delete guard, but its origin field must still be consumed or
        # "specs/old.md" would be read as the next record's status.
        self.assertEqual(
            self._pending(
                b"RD specs/gone.md\x00specs/old.md\x00?? specs/next.md\x00"
            ),
            [("??", "specs/next.md")],
        )

    def test_arrow_in_an_ordinary_filename_is_left_alone(self) -> None:
        # A non-rename record has no origin field, so an arrow inside its
        # path is just path.
        self.assertEqual(
            self._pending(b"?? specs/a -> b.md\x00"),
            [("??", "specs/a -> b.md")],
        )

    def test_unmerged_and_deleted_entries_are_dropped(self) -> None:
        # Nothing there to hold to a contract: an unmerged entry is a
        # merge in motion, and a "D" in either column means no file on
        # disk at that path.
        for record in [b"AA specs/a.md\x00", b"UU specs/a.md\x00",
                       b" D specs/a.md\x00", b"D  specs/a.md\x00"]:
            with self.subTest(record=record):
                self.assertEqual(self._pending(record), [])

    def test_nonascii_path_needs_no_unescaping(self) -> None:
        # The defect in issue #6: newline porcelain C-quoted this path as
        # "specs/caf\\303\\251.md" and the old strip/replace parse turned
        # the escapes into phantom directories. `-z` emits the raw UTF-8
        # bytes, so the decoded path is simply the file on disk.
        self.assertEqual(
            self._pending(b"?? specs/caf\xc3\xa9.md\x00"),
            [("??", "specs/café.md")],
        )

    def test_backslash_in_a_filename_is_preserved(self) -> None:
        # The row that rejects `core.quotepath=false` as a fix: git escapes
        # backslashes regardless of that setting, so only `-z` delivers the
        # literal byte - and it is a filename character on POSIX, not a
        # separator to normalise to "/".
        self.assertEqual(
            self._pending(b"?? specs/a\\b.md\x00"),
            [("??", "specs/a\\b.md")],
        )

    def test_a_quote_is_a_literal_filename_character(self) -> None:
        # Inverts the retired `test_quoted_paths_are_unquoted`: newline
        # porcelain wrapped non-plain paths in quotes and the parse stripped
        # them, taking a genuine leading/trailing `"` with it. Under `-z`
        # git never quotes, so a `"` in the payload IS the filename.
        self.assertEqual(
            self._pending(b'?? "specs/a.md"\x00'),
            [("??", '"specs/a.md"')],
        )

    def test_invalid_utf8_does_not_raise(self) -> None:
        # `surrogateescape` turns a malformed byte into a path that matches
        # no plan, rather than a UnicodeDecodeError no caller catches -
        # exit 2 is reserved for hard blocks, never a crashed gate.
        self.assertEqual(
            self._pending(b"?? specs/\xff.md\x00"),
            [("??", "specs/\udcff.md")],
        )

    def test_short_records_are_skipped(self) -> None:
        # Also covers the empty field after the final NUL terminator.
        self.assertEqual(self._pending(b"??\x00"), [])

    def test_git_failure_degrades_to_empty(self) -> None:
        # No repository means no verdict rather than a crash.
        with mock.patch(
            "_common.subprocess.run",
            return_value=_status_proc(b"fatal", returncode=128),
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

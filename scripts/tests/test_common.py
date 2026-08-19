"""Layer A: every public function in `_common.py`.

NOTE: `git_pending_paths` is tested against a mocked `subprocess.run` here;
the porcelain matrix proves against real git that the fixtures are shaped like
the records it emits.

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

from .support import TempDirCase, make_icm_tree, utf8_stdin, write_bytes


def _status_proc(stdout: bytes, returncode: int = 0) -> mock.Mock:
    """A canned `git status` result for patching `_common.subprocess.run`.

    NOTE: `stdout` is bytes, as `subprocess.run` returns without `text=True`:
    production decodes the `-z` NUL records by hand (issue #6), so a str here
    would test a decode path that no longer exists.
    """
    return mock.Mock(returncode=returncode, stdout=stdout)


class ReadEventTests(unittest.TestCase):
    def test_parses_a_json_object(self) -> None:
        """Check that a JSON object is parsed from stdin."""
        event = {"cwd": "/x", "stop_hook_active": False}
        with mock.patch("sys.stdin", utf8_stdin(json.dumps(event))):
            self.assertEqual(_common.read_event(), event)

    def test_invalid_json_degrades_to_empty(self) -> None:
        """Check that invalid JSON degrades to an empty dict."""
        with mock.patch("sys.stdin", utf8_stdin("not json")):
            self.assertEqual(_common.read_event(), {})

    def test_non_dict_json_degrades_to_empty(self) -> None:
        """Check that non-dict JSON degrades to an empty dict."""
        with mock.patch("sys.stdin", utf8_stdin("[1, 2]")):
            self.assertEqual(_common.read_event(), {})

    def test_reads_the_byte_layer_as_utf8(self) -> None:
        """Check that the byte layer is read as UTF-8.

        NOTE: `read_event` decodes `sys.stdin.buffer` as UTF-8 by hand
        (issue #14).
        """
        payload = json.dumps({"cwd": "/tmp/naïve-café"}, ensure_ascii=False)
        stand_in = io.TextIOWrapper(
            io.BytesIO(payload.encode("utf-8")), encoding="latin-1"
        )
        with mock.patch("sys.stdin", stand_in):
            self.assertEqual(
                _common.read_event(), {"cwd": "/tmp/naïve-café"}
            )

    def test_undecodable_bytes_degrade_without_raising(self) -> None:
        """Check that undecodable bytes degrade to an empty dict.

        NOTE: `read_event` decodes `sys.stdin.buffer` as UTF-8 by hand
        (issue #14)."""
        stand_in = io.TextIOWrapper(io.BytesIO(b"\xff\xfe"), encoding="utf-8")
        with mock.patch("sys.stdin", stand_in):
            self.assertEqual(_common.read_event(), {})


class ToolInputTests(unittest.TestCase):
    def test_returns_the_dict_when_present(self) -> None:
        """Check that the dict is returned when present."""
        event = {"tool_input": {"file_path": "/x/y.md"}}
        self.assertEqual(
            _common.tool_input(event), {"file_path": "/x/y.md"}
        )

    def test_absent_key_degrades_to_empty(self) -> None:
        """Check that an absent key degrades to an empty dict."""
        self.assertEqual(_common.tool_input({}), {})

    def test_null_degrades_to_empty(self) -> None:
        """Check that a null value degrades to an empty dict.

        NOTE: `tool_input` is expected to be a dict, but the event may have
        it set to None.
        """
        self.assertEqual(_common.tool_input({"tool_input": None}), {})

    def test_string_degrades_to_empty(self) -> None:
        """Check that a string value degrades to an empty dict."""
        self.assertEqual(
            _common.tool_input({"tool_input": "file_path"}), {}
        )

    def test_list_degrades_to_empty(self) -> None:
        """Check that a list value degrades to an empty dict."""
        self.assertEqual(
            _common.tool_input({"tool_input": ["/x/y.md"]}), {}
        )


class ProjectDirTests(unittest.TestCase):
    def test_resolves_cwd_from_the_event(self) -> None:
        """Check that the cwd from the event is resolved."""
        self.assertEqual(
            _common.project_dir({"cwd": "."}), Path(".").resolve()
        )

    def test_missing_cwd_falls_back_to_dot(self) -> None:
        """Check that a missing cwd falls back to the current directory."""
        self.assertEqual(_common.project_dir({}), Path(".").resolve())

    def test_falsy_cwd_falls_back_to_dot(self) -> None:
        """Check that a falsy cwd falls back to the current directory."""
        self.assertEqual(
            _common.project_dir({"cwd": ""}), Path(".").resolve()
        )
        self.assertEqual(
            _common.project_dir({"cwd": None}), Path(".").resolve()
        )

    def test_non_string_truthy_cwd_never_raises(self) -> None:
        """Check that a non-string truthy cwd never raises.

        NOTE: `project_dir` is expected to be a string, but the event may have
        it set to a non-string value.
        """

        for cwd in (42, True, ["a"], {"a": 1}):
            with self.subTest(cwd=cwd):
                self.assertEqual(
                    _common.project_dir({"cwd": cwd}),
                    Path(str(cwd)).resolve(),
                )


class IsIcmProjectTests(TempDirCase):
    scaffold_icm = False

    def test_false_without_the_marker(self) -> None:
        """Check that the marker file is required for an ICM project."""
        self.assertFalse(_common.is_icm_project(self.root))

    def test_true_once_icm_init_has_run(self) -> None:
        """Check that the marker file is created by `icm:init`."""
        make_icm_tree(self.root)
        self.assertTrue(_common.is_icm_project(self.root))


class RelativePosixTests(TempDirCase):
    scaffold_icm = False

    def test_inside_the_root_is_forward_slashed(self) -> None:
        """Check that a path inside the root is returned with `/`."""
        inside = self.root / "specs" / "commands" / "find.md"
        self.assertEqual(
            _common.relative_posix(str(inside), self.root),
            "specs/commands/find.md",
        )

    def test_outside_the_root_is_none(self) -> None:
        """Check that a path outside the root returns None."""
        outside = self.root.parent / "elsewhere.md"
        self.assertIsNone(_common.relative_posix(str(outside), self.root))

    def test_a_relative_path_anchors_on_root_not_process_cwd(self) -> None:
        """Check a relative path is anchored on the root, not the process cwd.

        NOTE: `Path(file_path).resolve()` anchored a relative path on the
        process actual cwd, contradicting the docstring (issue #15).
        """

        self.assertEqual(
            _common.relative_posix("specs/commands/find.md", self.root),
            "specs/commands/find.md",
        )

    def test_a_relative_path_escaping_root_is_none(self) -> None:
        self.assertIsNone(
            _common.relative_posix("../elsewhere.md", self.root)
        )


class FrontmatterLinesTests(unittest.TestCase):
    def test_returns_the_block_lines(self) -> None:
        """Check that the frontmatter block lines are returned."""
        text = "---\nstatus: done\npr: 7\n---\n\n# Plan\n"
        self.assertEqual(
            _common.frontmatter_lines(text), ["status: done", "pr: 7"]
        )

    def test_no_opening_fence_is_none(self) -> None:
        """Check that missing opening fence returns None."""
        self.assertIsNone(_common.frontmatter_lines("# Plan\n"))

    def test_unterminated_fence_is_none(self) -> None:
        """Check that an unterminated frontmatter fence returns None."""
        self.assertIsNone(_common.frontmatter_lines("---\nstatus: done\n"))


class ParsePlanFrontmatterTests(unittest.TestCase):
    def test_scalars_lists_and_hierarchy_keys(self) -> None:
        """Check that scalars, lists, and hierarchy keys are parsed."""
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
        """Check that inline list syntax is parsed."""
        meta = _common.parse_plan_frontmatter(
            "---\nspecs: [specs/a.md, specs/b.md]\n---\n"
        )
        assert meta is not None
        self.assertEqual(meta["specs"], ["specs/a.md", "specs/b.md"])

    def test_empty_values_read_as_none(self) -> None:
        """Check that empty frontmatter values are read as None."""
        meta = _common.parse_plan_frontmatter("---\nstatus:\npr:\n---\n")
        assert meta is not None
        self.assertIsNone(meta["status"])
        self.assertIsNone(meta["pr"])

    def test_no_frontmatter_is_none(self) -> None:
        """Check that no frontmatter returns None."""
        self.assertIsNone(_common.parse_plan_frontmatter("# Plan\n"))

    def test_quoted_block_entries_read_as_bare_paths(self) -> None:
        """Check that quoted block entries are read as bare paths.

        NOTE: Quoted block entries should be interpreted as bare paths,
        as quoting a value is ordinary YAML, which should not affect
        interpretation of the value.
        """

        meta = _common.parse_plan_frontmatter(
            "---\n"
            "specs:\n"
            '  - "specs/commands/a.md"\n'
            "  - 'specs/commands/b.md'\n"
            "---\n"
        )
        assert meta is not None
        self.assertEqual(
            meta["specs"], ["specs/commands/a.md", "specs/commands/b.md"]
        )

    def test_quoted_inline_list_mixed_quote_styles(self) -> None:
        """Check that quoted inline list entries are read as bare paths."""

        meta = _common.parse_plan_frontmatter(
            "---\n"
            "specs: [\"specs/a.md\", 'specs/b.md', specs/c.md]\n"
            "---\n"
        )
        assert meta is not None
        self.assertEqual(
            meta["specs"], ["specs/a.md", "specs/b.md", "specs/c.md"]
        )

    def test_a_hash_inside_quotes_is_not_a_comment(self) -> None:
        """Check that a hash inside quotes is not treated as a comment.

        NOTE: A hash inside quotes should not be treated as a comment.
        """

        meta = _common.parse_plan_frontmatter(
            '---\nspecs:\n  - "specs/a#b.md"\n---\n'
        )
        assert meta is not None
        self.assertEqual(meta["specs"], ["specs/a#b.md"])

    def test_a_quoted_entry_with_a_trailing_comment(self) -> None:
        """Check quoted entries with trailing comments are read as bare paths.

        NOTE: The trailing comment after a quoted entry should not affect the
        interpretation of the value.
        """

        meta = _common.parse_plan_frontmatter(
            '---\nspecs:\n  - "specs/a.md"  # trailing comment\n---\n'
        )
        assert meta is not None
        self.assertEqual(meta["specs"], ["specs/a.md"])

    def test_unbalanced_quotes_are_left_verbatim(self) -> None:
        """Check that unbalanced quotes are left verbatim.

        NOTE: Unbalanced quotes should be left verbatim, as they are not valid
        YAML and should not be interpreted as quoted values.
        """

        meta = _common.parse_plan_frontmatter(
            "---\n"
            "specs:\n"
            "  - specs/it's-a-file.md\n"
            '  - "specs/open.md\n'
            "---\n"
        )
        assert meta is not None
        self.assertEqual(
            meta["specs"], ["specs/it's-a-file.md", '"specs/open.md']
        )

    def test_a_quoted_status_reads_as_the_bare_enum_member(self) -> None:
        """Check that a quoted status reads as the bare enum member."""

        meta = _common.parse_plan_frontmatter('---\nstatus: "done"\n---\n')
        assert meta is not None
        self.assertEqual(meta["status"], "done")


class PlanSpecPathsTests(unittest.TestCase):
    def test_unions_both_fields_and_normalises_backslashes(self) -> None:
        """Check both fields are unioned and backslashes are normalised."""

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

    def test_quoted_frontmatter_flows_through_unquoted(self) -> None:
        """Check that quoted frontmatter flows through unquoted.

        NOTE: Quoted frontmatter should be interpreted as bare paths, so the
        coverage set holds keys a `git status` payload can actually match.
        """

        meta = _common.parse_plan_frontmatter(
            "---\n"
            'specs:\n  - "specs/a.md"\n'
            "authors:\n  - 'specs/b.md'\n"
            "---\n"
        )
        assert meta is not None
        self.assertEqual(
            _common.plan_spec_paths(meta), {"specs/a.md", "specs/b.md"}
        )


class IterPlansTests(TempDirCase):
    scaffold_icm = False

    def test_yields_sorted_plans_without_readme(self) -> None:
        """Check that plans are yielded sorted, without `README.md`."""
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
        """Check that a missing `plans` directory yields nothing."""
        self.assertEqual(list(_common.iter_plans(self.root)), [])

    def test_a_non_utf8_plan_does_not_stop_the_others(self) -> None:
        """Check that a non-UTF-8 plan does not stop the others."""

        write_bytes(self.root, "plans/bad.md", b"---\nstatus: caf\xe9\n---\n")
        (self.root / "plans" / "good.md").write_text(
            "# good", encoding="utf-8"
        )
        found = list(_common.iter_plans(self.root))
        self.assertEqual([path.name for path, _text in found], ["good.md"])

    def test_an_embedded_nul_path_does_not_stop_the_others(self) -> None:
        """Check that an embedded NUL path does not stop the others.
        
        NOTE: The residue of issue #8 (issue #17): a NUL in a path survives
        `resolve()` and `relative_to()` and only raises inside `read_text`,
        as a `ValueError`. No filesystem can hold a NUL filename.
        """

        plans = self.root / "plans"
        plans.mkdir()
        good = plans / "good.md"
        good.write_text("# good", encoding="utf-8")
        nul = plans / "bad\x00plan.md"
        with mock.patch.object(Path, "glob", return_value=[nul, good]):
            found = list(_common.iter_plans(self.root))
        self.assertEqual([path.name for path, _text in found], ["good.md"])


class GitPendingPathsTests(unittest.TestCase):
    """Parsing contract only - real git behaviour lives in the matrix.

    NOTE: Fixtures are NUL-terminated records of `git status --porcelain -z`
    (issue #6).
    """

    def _pending(
        self,
        stdout: bytes,
        root: Path | None = None,
        toplevel: mock.Mock | BaseException | None = None,
    ) -> list[tuple[str, str]]:
        """Run `git_pending_paths` with both subprocess calls faked.

        The first `subprocess.run` is the porcelain status call, the second
        is `git rev-parse --show-toplevel` (issue #13). By default the
        faked toplevel IS the root, so the computed prefix is empty and
        every payload passes through as-is - the shape of the historical
        single-call fixtures. Pass `toplevel` as a canned proc for a
        different toplevel, or as an exception instance to fail that call.
        """
        root = Path(".").resolve() if root is None else root
        if toplevel is None:
            toplevel = _status_proc(f"{root}\n".encode())
        with mock.patch(
            "_common.subprocess.run",
            side_effect=[_status_proc(stdout), toplevel],
        ):
            return _common.git_pending_paths(root, "specs")

    def test_status_column_is_positional(self) -> None:
        """Check that the status column is positional, not stripped."""

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
        """Check that a rename returns the destination path only."""

        self.assertEqual(
            self._pending(b"R  specs/new.md\x00specs/old.md\x00"),
            [("R ", "specs/new.md")],
        )
        self.assertEqual(
            self._pending(b"R  specs/a -> b.md\x00specs/c.md\x00"),
            [("R ", "specs/a -> b.md")],
        )

    def test_rename_consumes_the_origin_field(self) -> None:
        """Check a rename consumes the origin field & never misreads it."""

        self.assertEqual(
            self._pending(
                b"R  specs/new.md\x00specs/old.md\x00?? specs/b.md\x00"
            ),
            [("R ", "specs/new.md"), ("??", "specs/b.md")],
        )

    def test_dropped_rename_does_not_desync_the_stream(self) -> None:
        """Check that a dropped rename does not desync the stream."""

        self.assertEqual(
            self._pending(
                b"RD specs/gone.md\x00specs/old.md\x00?? specs/next.md\x00"
            ),
            [("??", "specs/next.md")],
        )

    def test_arrow_in_an_ordinary_filename_is_left_alone(self) -> None:
        """Check that an arrow in an ordinary filename is left alone."""

        self.assertEqual(
            self._pending(b"?? specs/a -> b.md\x00"),
            [("??", "specs/a -> b.md")],
        )

    def test_unmerged_and_deleted_entries_are_dropped(self) -> None:
        """Check that unmerged and deleted entries are dropped."""

        for record in [b"AA specs/a.md\x00", b"UU specs/a.md\x00",
                       b" D specs/a.md\x00", b"D  specs/a.md\x00"]:
            with self.subTest(record=record):
                self.assertEqual(self._pending(record), [])

    def test_nonascii_path_needs_no_unescaping(self) -> None:
        """Check that a non-ASCII path needs no unescaping."""

        self.assertEqual(
            self._pending(b"?? specs/caf\xc3\xa9.md\x00"),
            [("??", "specs/café.md")],
        )

    def test_backslash_in_a_filename_is_preserved(self) -> None:
        """Check that a backslash in a filename is preserved.

        NOTE: Git escapes backslashes in the porcelain output, so a literal
        backslash in a filename is always escaped. The `-z` option preserves
        the literal byte, so the filename is returned with the backslash
        intact.
        """

        self.assertEqual(
            self._pending(b"?? specs/a\\b.md\x00"),
            [("??", "specs/a\\b.md")],
        )

    def test_a_quote_is_a_literal_filename_character(self) -> None:
        """Check that a quote is a literal filename character."""

        self.assertEqual(
            self._pending(b'?? "specs/a.md"\x00'),
            [("??", '"specs/a.md"')],
        )

    def test_invalid_utf8_does_not_raise(self) -> None:
        """Check that invalid UTF-8 does not raise."""

        self.assertEqual(
            self._pending(b"?? specs/\xff.md\x00"),
            [("??", "specs/\udcff.md")],
        )

    def test_short_records_are_skipped(self) -> None:
        """Check that short records are skipped."""

        self.assertEqual(self._pending(b"??\x00"), [])

    def test_toplevel_prefix_is_rebased_onto_the_root(self) -> None:
        """Check that the toplevel prefix is rebased onto the root.

        NOTE: Porcelain reports paths relative to the repository toplevel
        regardless of `cwd`, while every caller compares against
        ICM-root-relative paths.
        """

        repo = Path(".").resolve()
        nested = repo / "sub"
        def top_ok() -> mock.Mock:
            return _status_proc(f"{repo}\n".encode())

        rows = [
            (
                "icm root is the repo root: prefix empty",
                repo,
                top_ok(),
                b"?? specs/a.md\x00",
                [("??", "specs/a.md")],
            ),
            (
                "icm root nested one level: prefix stripped",
                nested,
                top_ok(),
                b"?? sub/specs/a.md\x00A  sub/plans/p.md\x00",
                [("??", "specs/a.md"), ("A ", "plans/p.md")],
            ),
            (
                "prefix matches whole components only, never a sibling",
                nested,
                top_ok(),
                b"?? subx/specs/a.md\x00",
                [("??", "subx/specs/a.md")],
            ),
            (
                "rev-parse missing git: degrade to passthrough",
                nested,
                OSError("no git"),
                b"?? sub/specs/a.md\x00",
                [("??", "sub/specs/a.md")],
            ),
            (
                "rev-parse timeout: degrade to passthrough",
                nested,
                subprocess.TimeoutExpired("git", 15),
                b"?? sub/specs/a.md\x00",
                [("??", "sub/specs/a.md")],
            ),
            (
                "rev-parse non-zero (not a repo): degrade to passthrough",
                nested,
                _status_proc(b"fatal", returncode=128),
                b"?? sub/specs/a.md\x00",
                [("??", "sub/specs/a.md")],
            ),
            (
                # The adversarial row: `root` outside the decoded toplevel
                # (differing symlink resolution, fixtures) must degrade,
                # not raise an uncaught ValueError out of the gate.
                "root not below the toplevel: degrade to passthrough",
                nested,
                _status_proc(f"{repo / 'elsewhere'}\n".encode()),
                b"?? sub/specs/a.md\x00",
                [("??", "sub/specs/a.md")],
            ),
        ]
        for name, root, toplevel, stdout, expected in rows:
            with self.subTest(name=name):
                self.assertEqual(
                    self._pending(stdout, root=root, toplevel=toplevel),
                    expected,
                )

    def test_git_failure_degrades_to_empty(self) -> None:
        """Check that a git failure degrades to an empty list."""

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
        """Check that hook-specific output is written as JSON."""
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

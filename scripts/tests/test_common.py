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
        event = {"cwd": "/x", "stop_hook_active": False}
        with mock.patch("sys.stdin", utf8_stdin(json.dumps(event))):
            self.assertEqual(_common.read_event(), event)

    def test_invalid_json_degrades_to_empty(self) -> None:
        # Exit 2 is reserved for hard blocks; a malformed event must never
        # crash a gate, so the parse failure degrades to {}.
        with mock.patch("sys.stdin", utf8_stdin("not json")):
            self.assertEqual(_common.read_event(), {})

    def test_non_dict_json_degrades_to_empty(self) -> None:
        with mock.patch("sys.stdin", utf8_stdin("[1, 2]")):
            self.assertEqual(_common.read_event(), {})

    def test_reads_the_byte_layer_as_utf8(self) -> None:
        # `read_event` decodes `sys.stdin.buffer` as UTF-8 by hand
        # (issue #14) - a text-mode `json.load(sys.stdin)` would take the
        # wrapper's own (here deliberately wrong) encoding instead.
        payload = json.dumps({"cwd": "/tmp/naïve-café"}, ensure_ascii=False)
        stand_in = io.TextIOWrapper(
            io.BytesIO(payload.encode("utf-8")), encoding="latin-1"
        )
        with mock.patch("sys.stdin", stand_in):
            self.assertEqual(
                _common.read_event(), {"cwd": "/tmp/naïve-café"}
            )

    def test_undecodable_bytes_degrade_without_raising(self) -> None:
        # `errors="replace"` turns a stray non-UTF-8 byte into U+FFFD; the
        # result is not valid JSON here, so the parse arm degrades to {}.
        stand_in = io.TextIOWrapper(io.BytesIO(b"\xff\xfe"), encoding="utf-8")
        with mock.patch("sys.stdin", stand_in):
            self.assertEqual(_common.read_event(), {})


class ToolInputTests(unittest.TestCase):
    def test_returns_the_dict_when_present(self) -> None:
        event = {"tool_input": {"file_path": "/x/y.md"}}
        self.assertEqual(
            _common.tool_input(event), {"file_path": "/x/y.md"}
        )

    def test_absent_key_degrades_to_empty(self) -> None:
        self.assertEqual(_common.tool_input({}), {})

    def test_null_degrades_to_empty(self) -> None:
        # `event.get("tool_input", {})` only defaults when the key is
        # *absent* (issue #15): a present-but-non-dict value sailed past
        # and raised `AttributeError` on the chained `.get`.
        self.assertEqual(_common.tool_input({"tool_input": None}), {})

    def test_string_degrades_to_empty(self) -> None:
        self.assertEqual(
            _common.tool_input({"tool_input": "file_path"}), {}
        )

    def test_list_degrades_to_empty(self) -> None:
        self.assertEqual(
            _common.tool_input({"tool_input": ["/x/y.md"]}), {}
        )


class ProjectDirTests(unittest.TestCase):
    def test_resolves_cwd_from_the_event(self) -> None:
        self.assertEqual(
            _common.project_dir({"cwd": "."}), Path(".").resolve()
        )

    def test_missing_cwd_falls_back_to_dot(self) -> None:
        self.assertEqual(_common.project_dir({}), Path(".").resolve())

    def test_falsy_cwd_falls_back_to_dot(self) -> None:
        self.assertEqual(
            _common.project_dir({"cwd": ""}), Path(".").resolve()
        )
        self.assertEqual(
            _common.project_dir({"cwd": None}), Path(".").resolve()
        )

    def test_non_string_truthy_cwd_never_raises(self) -> None:
        # `or "."` only guards a *falsy* cwd (issue #15): a truthy
        # non-string (int, True, list, dict) reached `Path()` unguarded
        # and raised `TypeError` out of every gate - notably crashing
        # `gate_implement` *open*. The `str()` coercion stringifies the
        # value into a path that resolves somewhere harmless instead.
        for cwd in (42, True, ["a"], {"a": 1}):
            with self.subTest(cwd=cwd):
                self.assertEqual(
                    _common.project_dir({"cwd": cwd}),
                    Path(str(cwd)).resolve(),
                )


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

    def test_a_relative_path_anchors_on_root_not_process_cwd(self) -> None:
        # `Path(file_path).resolve()` anchored a relative path on the
        # process's actual cwd, contradicting the docstring (issue #15) -
        # and the one direction that could fail in was a silent ALLOW.
        # `Path(root, file_path)` resolves it against `root` instead.
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

    def test_quoted_block_entries_read_as_bare_paths(self) -> None:
        # The defect in issue #9: quoting a value is ordinary YAML, but the
        # quote characters survived into the parsed entry, so the coverage
        # key matched no path on disk and gate_spec_coverage blocked the
        # Stop naming a spec the plan demonstrably owned.
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
        # Issue #9's exact fixture: flow-sequence elements unquote
        # per-element, each in its author's own quote style.
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
        # The row that distinguishes the quote-aware `_strip_comment` from
        # a naive reorder of strip and unquote: splitting on the first `#`
        # unconditionally truncated this entry to `"specs/a` before any
        # unquoting could see the pair (issue #9).
        meta = _common.parse_plan_frontmatter(
            '---\nspecs:\n  - "specs/a#b.md"\n---\n'
        )
        assert meta is not None
        self.assertEqual(meta["specs"], ["specs/a#b.md"])

    def test_a_quoted_entry_with_a_trailing_comment(self) -> None:
        # The `#` after the closing quote is back outside the quoted
        # region, so it is a comment again.
        meta = _common.parse_plan_frontmatter(
            '---\nspecs:\n  - "specs/a.md"  # trailing comment\n---\n'
        )
        assert meta is not None
        self.assertEqual(meta["specs"], ["specs/a.md"])

    def test_unbalanced_quotes_are_left_verbatim(self) -> None:
        # `_unquote` strips exactly one matching surrounding pair: an
        # internal apostrophe is a filename character, and an unterminated
        # quote is the author's typo for a gate to name as written, not
        # the parser's to guess at (issue #9).
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
        # `status: "done"` is legal YAML today; the scalar site unquotes
        # too, so it must not read as off-enum (issue #9).
        meta = _common.parse_plan_frontmatter('---\nstatus: "done"\n---\n')
        assert meta is not None
        self.assertEqual(meta["status"], "done")


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

    def test_quoted_frontmatter_flows_through_unquoted(self) -> None:
        # End-to-end over the two helpers (issue #9): a quoted plan parses
        # to bare paths, so the coverage set holds keys a `git status`
        # payload can actually match.
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

    def test_a_non_utf8_plan_does_not_stop_the_others(self) -> None:
        # The defect in issue #8: `UnicodeDecodeError` is a `ValueError`,
        # which `except OSError` never caught, so one latin-1 plan aborted
        # the generator out of the caller's loop and took Invariant 1 down
        # for the whole tree. The load-bearing assertion is that the good
        # plan is still yielded - "bad.md" sorts first, so the generator
        # must survive it to get there - not merely that nothing raises.
        write_bytes(self.root, "plans/bad.md", b"---\nstatus: caf\xe9\n---\n")
        (self.root / "plans" / "good.md").write_text(
            "# good", encoding="utf-8"
        )
        found = list(_common.iter_plans(self.root))
        self.assertEqual([path.name for path, _text in found], ["good.md"])

    def test_an_embedded_nul_path_does_not_stop_the_others(self) -> None:
        # The residue of issue #8 (issue #17): a NUL in a path survives
        # `resolve()` and `relative_to()` and only raises inside
        # `read_text`, as a `ValueError` that is NOT a `UnicodeDecodeError`
        # - so the guard narrowed to `(OSError, UnicodeDecodeError)` still
        # let it abort the generator. No filesystem can hold a NUL
        # filename, so the glob is patched to inject one; the `read_text`
        # that raises is real, and the good plan sorting after it must
        # still be yielded.
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

    Fixtures are the NUL-terminated records of `git status --porcelain -z`
    (issue #6): `XY <path>\\0`, with a rename's origin as its own trailing
    field. The characters `-z` exists for - non-ASCII, `"`, backslash -
    cannot be created on NTFS, so the mocked bytes here are the only place
    those trigger classes are testable; the matrix covers what real git on
    this filesystem can produce.
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

    def test_toplevel_prefix_is_rebased_onto_the_root(self) -> None:
        # The defect in issue #13: porcelain reports paths relative to the
        # repository toplevel regardless of `cwd`, while every caller
        # compares against ICM-root-relative paths - so a nested ICM tree
        # could only clear coverage with frontmatter that was wrong. Rows
        # are `(root, toplevel, stdout, expected)`: the prefix is stripped
        # when the tree is nested, empty when root IS the toplevel, and any
        # failure to establish the toplevel degrades to passthrough.
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

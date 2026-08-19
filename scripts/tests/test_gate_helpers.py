"""Layer A: the gate scripts' own pure helpers, no subprocess.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import json
import unittest

import gate_closeout
import gate_output_naming
import gate_spec_coverage
import preflight

from .support import SCRIPTS


class IsArrivingTests(unittest.TestCase):
    """Codes no cheap fixture produces, asserted against the predicate.

    NOTE: "UA" never matched the issue's proposed `status[0] in "A?RC"`
    either way - the merge codes are asymmetric, and pinning that
    asymmetry is the point: one merge must not mean two things depending
    on which parent wrote the file. No repository is needed here, which
    is half of why the predicate exists as a function at all.
    """

    def test_table(self) -> None:
        table = {
            "??": True,
            "A ": True,
            "AM": True,
            "R ": True,
            "RM": True,
            "C ": True,
            " M": False,
            "M ": False,
            "MM": False,
            "AA": False,
            "AU": False,
            "UA": False,
            "UU": False,
        }
        for code, expected in table.items():
            with self.subTest(code=code):
                self.assertIs(
                    gate_spec_coverage.is_arriving(code), expected
                )


class SectionTests(unittest.TestCase):
    """`gate_closeout.section` - the closeout verdict's text scanner."""

    TEXT = (
        "# Plan\n\n## Validation\n\n- [x] a\n- [ ] b\n\n"
        "## Notes\n\nBox b untestable offline.\n"
    )

    def test_body_runs_to_the_next_h2(self) -> None:
        self.assertEqual(
            gate_closeout.section(self.TEXT, "Validation"),
            "- [x] a\n- [ ] b",
        )

    def test_last_section_runs_to_end_of_file(self) -> None:
        self.assertEqual(
            gate_closeout.section(self.TEXT, "Notes"),
            "Box b untestable offline.",
        )

    def test_missing_section_is_empty(self) -> None:
        # An empty Notes section and an absent one must read the same:
        # both mean no reason was recorded.
        self.assertEqual(gate_closeout.section(self.TEXT, "Scope"), "")


class OutputPathRegexTests(unittest.TestCase):
    """`OUTPUT_RE` and `NAME_RE` - the naming gate's whole verdict."""

    def test_output_re_matches_stage_output_paths_only(self) -> None:
        rows = {
            "ICM/process-plan/stages/01-specification/output/x.md": True,
            "ICM/express-change/stages/02-implementation/output/a.md": True,
            "ICM/process-plan/stages/01-specification/x.md": False,
            "specs/commands/find.md": False,
            "plans/x.md": False,
        }
        for path, expected in rows.items():
            with self.subTest(path=path):
                match = gate_output_naming.OUTPUT_RE.match(path)
                self.assertIs(match is not None, expected)

    def test_output_re_captures_workspace_stage_number_and_name(self) -> None:
        match = gate_output_naming.OUTPUT_RE.match(
            "ICM/process-plan/stages/01-specification/output/a-spec.md"
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.groups(), ("process-plan", "01", "a-spec.md"))

    def test_name_re_enforces_kebab_slug_and_suffix(self) -> None:
        rows = {
            "my-feature-spec.md": ("my-feature", "spec"),
            "x-code.md": ("x", "code"),
            "a-b-c-test.md": ("a-b-c", "test"),
            "my-feature-docs.md": ("my-feature", "docs"),
            "notes.md": None,
            "My-Feature-spec.md": None,
            "my_feature-spec.md": None,
            "my-feature-spec.txt": None,
            "-spec.md": None,
        }
        for name, expected in rows.items():
            with self.subTest(name=name):
                match = gate_output_naming.NAME_RE.match(name)
                if expected is None:
                    self.assertIsNone(match)
                else:
                    assert match is not None
                    self.assertEqual(match.groups(), expected)


class PluginVersionTests(unittest.TestCase):
    def test_reads_the_authoritative_manifest_field(self) -> None:
        manifest = SCRIPTS.parent / ".claude-plugin" / "plugin.json"
        expected = json.loads(manifest.read_text(encoding="utf-8"))[
            "version"
        ]
        self.assertEqual(preflight.plugin_version(), expected)
        self.assertNotEqual(preflight.plugin_version(), "unknown")


if __name__ == "__main__":
    unittest.main()

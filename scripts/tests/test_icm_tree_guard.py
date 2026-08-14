"""Layer B: without `ICM/` every gate stays silent.

Whatever scope the plugin was installed at, its hooks fire in unrelated
repositories too - including any that happen to own a `specs/` or
`plans/` directory. Every case below blocks in a real ICM project.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_clarification
import gate_closeout
import gate_implement
import gate_output_naming
import gate_plan_frontmatter
import gate_spec_coverage
import gate_spec_edit
import preflight

from .support import TempDirCase, call_gate_main, write_plan


class IcmTreeGuardTests(TempDirCase):
    scaffold_icm = False  # the absence of ICM/ is the case under test
    scaffold_git = True

    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs" / "commands").mkdir(parents=True)
        (self.root / "specs" / "commands" / "orphan.md").write_text(
            "# spec", encoding="utf-8"
        )
        write_plan(self.root, "half-closed", status="done", pr="")
        write_plan(self.root, "bogus", status="bogus")

    def _stop_event(self) -> dict:
        return {"cwd": str(self.root), "stop_hook_active": False}

    def test_fixture_has_no_icm_directory(self) -> None:
        self.assertFalse((self.root / "ICM").exists())

    def test_gate_implement_stays_silent(self) -> None:
        rc, _out, err = call_gate_main(
            gate_implement,
            {"cwd": str(self.root), "prompt": "/icm:implement x"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_gate_clarification_stays_silent(self) -> None:
        rc, _out, err = call_gate_main(
            gate_clarification,
            {"cwd": str(self.root), "prompt": "/icm:implement x"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_gate_spec_edit_stays_silent(self) -> None:
        _rc, out, _err = call_gate_main(
            gate_spec_edit,
            {
                "cwd": str(self.root),
                "tool_input": {
                    "file_path": str(
                        self.root / "specs" / "commands" / "orphan.md"
                    )
                },
            },
        )
        self.assertEqual(out.strip(), "")

    def test_gate_plan_frontmatter_stays_silent(self) -> None:
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter,
            {
                "cwd": str(self.root),
                "tool_input": {
                    "file_path": str(self.root / "plans" / "bogus.md")
                },
            },
        )
        self.assertEqual(out.strip(), "")

    def test_gate_spec_coverage_stays_silent(self) -> None:
        rc, _out, err = call_gate_main(
            gate_spec_coverage, self._stop_event()
        )
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_gate_closeout_stays_silent(self) -> None:
        rc, _out, err = call_gate_main(gate_closeout, self._stop_event())
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_gate_output_naming_stays_silent(self) -> None:
        # gate_output_naming is guarded by its path shape (OUTPUT_RE)
        # rather than by is_icm_project, so the silence to assert is a
        # write that matches nothing under ICM/*/stages/*/output/.
        _rc, out, _err = call_gate_main(
            gate_output_naming,
            {
                "cwd": str(self.root),
                "tool_input": {
                    "file_path": str(
                        self.root / "specs" / "commands" / "orphan.md"
                    )
                },
            },
        )
        self.assertEqual(out.strip(), "")

    def test_preflight_stays_silent(self) -> None:
        rc, out, _err = call_gate_main(
            preflight, {"cwd": str(self.root), "source": "startup"}
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()

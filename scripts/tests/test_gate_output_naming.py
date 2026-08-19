"""Layer B: `gate_output_naming.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_output_naming

from .support import TempDirCase, call_gate_main, specific_output


class GateOutputNamingTests(TempDirCase):
    def setUp(self) -> None:
        """Set up the stage 01 output directory."""
        super().setUp()
        self.stage01 = (
            self.root
            / "ICM"
            / "process-plan"
            / "stages"
            / "01-specification"
            / "output"
        )

    def _event(self, path: str) -> dict:
        return {
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.stage01 / path)},
        }

    def test_denies_a_stray_output_name(self) -> None:
        """Check that the gate denies a stray output name in stage 01."""

        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event("notes.md")
        )
        self.assertEqual(
            specific_output(out).get("permissionDecision"), "deny"
        )

    def test_denies_the_wrong_stage_suffix(self) -> None:
        """Check an incorrect stage 01 output name is denied."""

        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event("my-feature-code.md")
        )
        self.assertEqual(
            specific_output(out).get("permissionDecision"), "deny"
        )

    def test_passes_slug_spec_in_stage_01(self) -> None:
        """Check a correct stage 01 output name is allowed."""

        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event("my-feature-spec.md")
        )
        self.assertEqual(out.strip(), "")

    def test_passes_gitkeep(self) -> None:
        """Check that the gate passes a `.gitkeep` file in stage 01."""

        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event(".gitkeep")
        )
        self.assertEqual(out.strip(), "")

    def test_a_malformed_tool_input_degrades_to_silence(self) -> None:
        """Check that a malformed `tool_input` does not crash the gate."""

        for tool_input in (None, "file_path", ["/x/y.md"]):
            with self.subTest(tool_input=tool_input):
                rc, out, _err = call_gate_main(
                    gate_output_naming,
                    {"cwd": str(self.root), "tool_input": tool_input},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(out.strip(), "")

    def test_silent_outside_output(self) -> None:
        """Check that the gate is silent outside of `output/`."""

        event = {
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.root / "plans" / "x.md")},
        }
        _rc, out, _err = call_gate_main(gate_output_naming, event)
        self.assertEqual(out.strip(), "")

    def test_silent_in_workspaces_without_output_artifacts(self) -> None:
        """Check the gate is silent in workspaces without artifacts."""

        for name in ("my-feature-spec.md", "my-feature-change.md"):
            with self.subTest(name=name):
                path = (
                    self.root
                    / "ICM"
                    / "express-change"
                    / "stages"
                    / "01-change"
                    / "output"
                    / name
                )
                rc, out, _err = call_gate_main(
                    gate_output_naming,
                    {
                        "cwd": str(self.root),
                        "tool_input": {"file_path": str(path)},
                    },
                )
                self.assertEqual(rc, 0)
                self.assertEqual(out.strip(), "")


class GateOutputNamingNoIcmTests(TempDirCase):
    """The gate must no-op entirely when there is no `ICM/` tree."""

    scaffold_icm = False

    def test_silent_without_icm_directory(self) -> None:
        """Check that the gate is silent without a `ICM/` directory."""

        path = (
            self.root
            / "ICM"
            / "process-plan"
            / "stages"
            / "01-specification"
            / "output"
            / "notes.md"
        )
        rc, out, _err = call_gate_main(
            gate_output_naming,
            {
                "cwd": str(self.root),
                "tool_input": {"file_path": str(path)},
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()

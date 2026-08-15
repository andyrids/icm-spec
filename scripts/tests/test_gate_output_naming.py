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
        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event("notes.md")
        )
        self.assertEqual(
            specific_output(out).get("permissionDecision"), "deny"
        )

    def test_denies_the_wrong_stage_suffix(self) -> None:
        # The slug correlates a run's artifacts across all four stages,
        # so `-code` in stage 01 breaks the handoff chain even though it
        # is a valid suffix somewhere.
        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event("my-feature-code.md")
        )
        self.assertEqual(
            specific_output(out).get("permissionDecision"), "deny"
        )

    def test_passes_slug_spec_in_stage_01(self) -> None:
        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event("my-feature-spec.md")
        )
        self.assertEqual(out.strip(), "")

    def test_passes_gitkeep(self) -> None:
        _rc, out, _err = call_gate_main(
            gate_output_naming, self._event(".gitkeep")
        )
        self.assertEqual(out.strip(), "")

    def test_silent_outside_output(self) -> None:
        event = {
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.root / "plans" / "x.md")},
        }
        _rc, out, _err = call_gate_main(gate_output_naming, event)
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()

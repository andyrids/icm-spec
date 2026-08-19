"""Layer B: `gate_spec_edit.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_spec_edit

from .support import TempDirCase, call_gate_main, specific_output


class GateSpecEditTests(TempDirCase):
    def _event(self, *parts: str) -> dict:
        return {
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.root.joinpath(*parts))},
        }

    def test_asks_on_specs_write(self) -> None:
        # Never a hard deny - spec amendment is legitimate stage-01
        # re-entry work; the human is the gate, and the reason must name
        # the stage rule so the approval is informed.
        _rc, out, _err = call_gate_main(
            gate_spec_edit, self._event("specs", "commands", "find.md")
        )
        decision = specific_output(out)
        self.assertEqual(decision.get("permissionDecision"), "ask")
        self.assertIn(
            "stage 01", decision.get("permissionDecisionReason", "")
        )

    def test_silent_outside_specs(self) -> None:
        rc, out, _err = call_gate_main(
            gate_spec_edit, self._event("src", "x.py")
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")

    def test_a_malformed_tool_input_degrades_to_silence(self) -> None:
        # `read_event` only guards the top-level event (issue #15): a
        # present-but-non-dict `tool_input` crashed the gate with an
        # `AttributeError` on the chained `.get`. It must degrade to
        # exit 0 with no verdict instead.
        for tool_input in (None, "file_path", ["/x/y.md"]):
            with self.subTest(tool_input=tool_input):
                rc, out, _err = call_gate_main(
                    gate_spec_edit,
                    {"cwd": str(self.root), "tool_input": tool_input},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(out.strip(), "")

    def test_silent_for_examples_specs(self) -> None:
        # Only the top-level tree declares desired state; a nested
        # `specs/` directory is somebody else's example.
        _rc, out, _err = call_gate_main(
            gate_spec_edit, self._event("examples", "specs", "a.md")
        )
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()

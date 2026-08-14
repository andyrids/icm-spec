"""Layer B: `preflight.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import preflight

from .support import TempDirCase, call_gate_main, specific_output


class PreflightTests(TempDirCase):
    def test_names_the_session_start_event(self) -> None:
        _rc, out, _err = call_gate_main(
            preflight, {"cwd": str(self.root), "source": "startup"}
        )
        self.assertEqual(
            specific_output(out).get("hookEventName"), "SessionStart"
        )

    def test_announces_the_armed_gates_in_an_icm_tree(self) -> None:
        # The line is the positive signal; its absence in a scaffolded
        # repository is the tell that the hook runtime is broken.
        rc, out, _err = call_gate_main(
            preflight, {"cwd": str(self.root), "source": "startup"}
        )
        self.assertEqual(rc, 0)
        self.assertIn(
            "gates armed", specific_output(out).get("additionalContext", "")
        )


if __name__ == "__main__":
    unittest.main()

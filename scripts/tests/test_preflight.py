"""Layer B: `preflight.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest
from unittest import mock

import preflight

from .support import (
    TempDirCase,
    call_gate_main,
    specific_output,
    write_bytes,
)


class PreflightTests(TempDirCase):
    def test_names_the_session_start_event(self) -> None:
        """Check positive signal of the SessionStart event name in the output.

        NOTE: Ensures that the hook runtime is not broken by looking for the
        positive signal of the SessionStart event name in the output.
        """

        _rc, out, _err = call_gate_main(
            preflight, {"cwd": str(self.root), "source": "startup"}
        )
        self.assertEqual(
            specific_output(out).get("hookEventName"), "SessionStart"
        )

    def test_announces_the_armed_gates_in_an_icm_tree(self) -> None:
        """Check positive signal of the "gates armed" message in output."""

        rc, out, _err = call_gate_main(
            preflight, {"cwd": str(self.root), "source": "startup"}
        )
        self.assertEqual(rc, 0)
        self.assertIn(
            "gates armed", specific_output(out).get("additionalContext", "")
        )

    def test_a_non_utf8_manifest_still_emits_the_banner(self) -> None:
        """Check that a non-UTF-8 manifest still emits the banner."""

        write_bytes(
            self.root,
            ".claude-plugin/plugin.json",
            b'{"version": "caf\xe9"}',
        )
        with mock.patch.object(
            preflight, "SCRIPTS", self.root / "scripts"
        ):
            rc, out, _err = call_gate_main(
                preflight, {"cwd": str(self.root), "source": "startup"}
            )
        self.assertEqual(rc, 0)
        context = specific_output(out).get("additionalContext", "")
        self.assertIn("icm unknown preflight", context)
        self.assertIn("gates armed", context)


if __name__ == "__main__":
    unittest.main()

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

    def test_a_non_utf8_manifest_still_emits_the_banner(self) -> None:
        # `UnicodeDecodeError` is raised by `read_text`, not `json.loads`,
        # so neither guard caught it (issue #8) - and the banner is the
        # positive signal, so it must degrade to "unknown" rather than
        # vanish and read as a broken hook runtime. `SCRIPTS` is patched
        # into the tempdir so `plugin_version` resolves the fixture
        # manifest instead of the repository's own.
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

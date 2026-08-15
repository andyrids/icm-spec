"""Layer B: `gate_clarification.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import shutil
import unittest

import gate_clarification

from .support import TempDirCase, call_gate_main, write_bytes


class GateClarificationTests(TempDirCase):
    def setUp(self) -> None:
        super().setUp()
        self.outdir = (
            self.root
            / "ICM"
            / "process-plan"
            / "stages"
            / "01-specification"
            / "output"
        )
        self.event = {
            "cwd": str(self.root),
            "prompt": "/icm:implement my-feature",
        }

    def test_passes_with_no_stage01_output(self) -> None:
        # The express path and a cleaned-scratch re-entry have no stage
        # 01 output at all, and neither may be blocked.
        shutil.rmtree(self.outdir)
        rc, _out, err = call_gate_main(gate_clarification, self.event)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_blocks_on_an_unresolved_marker(self) -> None:
        (self.outdir / "my-feature-spec.md").write_text(
            "# Technical spec\n\nAuth is "
            "[NEEDS CLARIFICATION: which token scheme?] for now.\n",
            encoding="utf-8",
        )
        rc, _out, err = call_gate_main(gate_clarification, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("which token scheme", err)
        self.assertIn("my-feature-spec.md", err)

    def test_passes_once_the_marker_is_resolved(self) -> None:
        (self.outdir / "my-feature-spec.md").write_text(
            "# Technical spec\n\nAuth is bearer tokens.\n",
            encoding="utf-8",
        )
        rc, _out, err = call_gate_main(gate_clarification, self.event)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_a_non_utf8_scratch_file_does_not_stop_the_others(self) -> None:
        # `UnicodeDecodeError` is a `ValueError` that `except OSError`
        # never caught (issue #8): one non-UTF-8 scratch file aborted the
        # loop before the rest of the stage 01 output was scanned.
        # "aa-bad.md" sorts before the marker file, so the gate must
        # survive it to block - the open question still surfacing is the
        # load-bearing assertion, not the absence of a crash.
        write_bytes(
            self.root,
            "ICM/process-plan/stages/01-specification/output/aa-bad.md",
            b"# techspec caf\xe9\n",
        )
        (self.outdir / "my-feature-spec.md").write_text(
            "Auth is [NEEDS CLARIFICATION: which token scheme?] for now.\n",
            encoding="utf-8",
        )
        rc, _out, err = call_gate_main(gate_clarification, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("which token scheme", err)

    def test_ignores_other_prompts(self) -> None:
        (self.outdir / "my-feature-spec.md").write_text(
            "x [NEEDS CLARIFICATION: y?]", encoding="utf-8"
        )
        rc, _out, _err = call_gate_main(
            gate_clarification,
            {"cwd": str(self.root), "prompt": "/icm:specify x"},
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

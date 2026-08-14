"""Layer B: `gate_closeout.main()` own-behaviour rows, real git repo.

The renamed-plan rows - the gate reading a plan at its rename
destination - live with the porcelain matrix in
`test_porcelain_matrix.py`.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_closeout

from .support import TempDirCase, call_gate_main, write_plan


class GateCloseoutTests(TempDirCase):
    scaffold_git = True

    def setUp(self) -> None:
        super().setUp()
        self.event = {"cwd": str(self.root), "stop_hook_active": False}

    def test_blocks_done_with_empty_pr(self) -> None:
        write_plan(self.root, "closing", status="done", pr="")
        rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("pr:", err)

    def test_blocks_unticked_boxes_with_empty_notes(self) -> None:
        write_plan(
            self.root,
            "unticked",
            status="done",
            pr="7",
            validation="- [x] a\n- [ ] b",
            notes="",
        )
        rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("unticked", err)

    def test_passes_unticked_boxes_with_a_notes_reason(self) -> None:
        # The closeout protocol permits unticked boxes - but only with
        # the reason recorded in Notes; silence is what hollows the
        # record out.
        write_plan(
            self.root,
            "excused",
            status="done",
            pr="7",
            validation="- [x] a\n- [ ] b",
            notes="Box b untestable offline.",
        )
        rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_passes_a_fully_ticked_closeout(self) -> None:
        write_plan(
            self.root,
            "ticked",
            status="done",
            pr="7",
            validation="- [x] a\n- [x] b",
        )
        rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_ignores_non_done_plans(self) -> None:
        write_plan(
            self.root, "open", status="in-progress", validation="- [ ] a"
        )
        rc, _out, _err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

"""Layer B: `gate_closeout.main()` own-behaviour rows, real git repo.

The renamed-plan rows - the gate reading a plan at its rename
destination - live with the porcelain matrix in
`test_porcelain_matrix.py`.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest
from unittest import mock

import gate_closeout

from .support import TempDirCase, call_gate_main, write_bytes, write_plan


class GateCloseoutTests(TempDirCase):
    scaffold_git = True

    def setUp(self) -> None:
        """Create a temp git repo with `plans/` subdir & `plan.md` file."""

        super().setUp()
        self.event = {"cwd": str(self.root), "stop_hook_active": False}

    def test_blocks_done_with_empty_pr(self) -> None:
        """Closeout protocol requires a PR number in the plan frontmatter."""

        write_plan(self.root, "closing", status="done", pr="")
        rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("pr:", err)

    def test_blocks_unticked_boxes_with_empty_notes(self) -> None:
        """Closeout protocol requires Notes to explain unticked boxes."""

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
        """Check closeout protocol permits unticked boxes with a reason."""

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
        """Check closeout protocol permits a fully ticked plan."""

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

    def test_a_non_utf8_plan_does_not_stop_the_others(self) -> None:
        """Check a non-UTF-8 plan does not stop others from being judged."""

        write_bytes(self.root, "plans/bad.md", b"---\nstatus: caf\xe9\n---\n")
        write_plan(self.root, "closing", status="done", pr="")
        rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("closing.md", err)

    def test_an_embedded_nul_path_does_not_stop_the_others(self) -> None:
        """Check that an embedded NUL path does not stop the others."""

        write_plan(self.root, "closing", status="done", pr="")
        pending = [
            ("??", "plans/bad\x00plan.md"),
            ("??", "plans/closing.md"),
        ]
        with mock.patch.object(
            gate_closeout, "git_pending_paths", return_value=pending
        ):
            rc, _out, err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 2)
        self.assertIn("closing.md", err)

    def test_ignores_non_done_plans(self) -> None:
        """Check that a non-done plan does not block the gate."""

        write_plan(
            self.root, "open", status="in-progress", validation="- [ ] a"
        )
        rc, _out, _err = call_gate_main(gate_closeout, self.event)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

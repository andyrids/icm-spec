"""Layer B: `gate_implement.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_implement

from .support import TempDirCase, call_gate_main, write_plan


class GateImplementTests(TempDirCase):
    def _event(self, prompt: str = "/icm:implement my-feature") -> dict:
        return {"cwd": str(self.root), "prompt": prompt}

    def test_blocks_with_no_open_plan(self) -> None:
        rc, _out, err = call_gate_main(gate_implement, self._event())
        self.assertEqual(rc, 2)
        self.assertIn("plan", err)

    def test_passes_with_a_planned_plan(self) -> None:
        write_plan(self.root, "my-feature", status="planned")
        rc, _out, _err = call_gate_main(gate_implement, self._event())
        self.assertEqual(rc, 0)

    def test_passes_with_an_in_progress_plan(self) -> None:
        # Stage 02 itself flips `planned` to `in-progress`, so both
        # states count as an open plan.
        write_plan(self.root, "my-feature", status="in-progress")
        rc, _out, _err = call_gate_main(gate_implement, self._event())
        self.assertEqual(rc, 0)

    def test_blocks_when_the_only_plan_is_done(self) -> None:
        write_plan(self.root, "my-feature", status="done", pr="1")
        rc, _out, _err = call_gate_main(gate_implement, self._event())
        self.assertEqual(rc, 2)

    def test_ignores_other_prompts(self) -> None:
        rc, _out, _err = call_gate_main(
            gate_implement, self._event("/icm:specify x")
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

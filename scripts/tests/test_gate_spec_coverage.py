"""Layer B: the spec-coverage gate's cumulative six-step flow.

The single-status regression rows live in `test_porcelain_matrix.py`;
this flow proves state *transitions* across one evolving repository, so
it stays cumulative by design.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_spec_coverage

from .support import (
    TempDirCase,
    call_gate_main,
    git_commit_all,
    write_plan,
)


class GateSpecCoverageFlowTests(TempDirCase):
    scaffold_git = True

    def test_six_step_flow(self) -> None:
        """Test the six-step flow of the spec-coverage gate."""

        root = self.root
        (root / "specs" / "commands").mkdir(parents=True)
        (root / "specs" / "README.md").write_text(
            "# Specs", encoding="utf-8"
        )
        (root / "specs" / "commands" / "orphan.md").write_text(
            "# spec", encoding="utf-8"
        )
        event = {"cwd": str(root), "stop_hook_active": False}

        with self.subTest("blocks an uncovered new spec"):
            rc, _out, err = call_gate_main(gate_spec_coverage, event)
            self.assertEqual(rc, 2)
            self.assertIn("orphan.md", err)

        with self.subTest("respects stop_hook_active"):
            rc, _out, _err = call_gate_main(
                gate_spec_coverage,
                {"cwd": str(root), "stop_hook_active": True},
            )
            self.assertEqual(rc, 0)

        # A plan that writes a spec without changing behaviour correctly
        # carries `specs: []`, so reading `specs:` alone would block the one
        # case plans/README.md calls correct and common.
        with self.subTest("authors: alone covers a spec-authoring plan"):
            write_plan(
                root,
                "author-only",
                authors="\n  - specs/commands/orphan.md",
            )
            rc, _out, err = call_gate_main(gate_spec_coverage, event)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")

        with self.subTest("blocks again with the authoring plan removed"):
            (root / "plans" / "author-only.md").unlink()
            rc, _out, _err = call_gate_main(gate_spec_coverage, event)
            self.assertEqual(rc, 2)

        with self.subTest("passes once a plan covers it"):
            write_plan(root, "owner", specs="\n  - specs/commands/orphan.md")
            rc, _out, err = call_gate_main(gate_spec_coverage, event)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")

        with self.subTest("modified committed specs do not block"):
            git_commit_all(root)
            (root / "specs" / "commands" / "orphan.md").write_text(
                "# spec v2", encoding="utf-8"
            )
            (root / "plans" / "owner.md").unlink()
            rc, _out, err = call_gate_main(gate_spec_coverage, event)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")

    def test_a_quoted_specs_entry_opens_the_gate(self) -> None:
        """Check a plan with a quoted spec path does not block the gate."""

        root = self.root
        (root / "specs" / "commands").mkdir(parents=True)
        (root / "specs" / "commands" / "quoted.md").write_text(
            "# spec", encoding="utf-8"
        )
        write_plan(root, "owner", specs='\n  - "specs/commands/quoted.md"')
        rc, _out, err = call_gate_main(
            gate_spec_coverage,
            {"cwd": str(root), "stop_hook_active": False},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()

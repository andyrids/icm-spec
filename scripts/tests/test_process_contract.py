"""Layer C: the deployed process contract, one real spawn per script.

Everything else in this suite calls `main()` in-process; only a real
subprocess proves what the hook runner actually deploys - the
`# /// script` header parses, `sys.exit(main())` maps the return value
onto a process exit, and the contract is JSON on stdin in, JSON on
stdout or an exit code out. One representative blocking or emitting
case each; behavioural breadth lives in the other layers.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

from .support import (
    TempDirCase,
    run_gate_subprocess,
    specific_output,
    write_plan,
)


class ProcessContractTests(TempDirCase):
    scaffold_git = True  # the two Stop gates read `git status`

    def test_gate_implement(self) -> None:
        proc = run_gate_subprocess(
            "gate_implement.py",
            {"cwd": str(self.root), "prompt": "/icm:implement x"},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("plan", proc.stderr)

    def test_gate_clarification(self) -> None:
        outdir = (
            self.root
            / "ICM"
            / "process-plan"
            / "stages"
            / "01-specification"
            / "output"
        )
        (outdir / "x-spec.md").write_text(
            "[NEEDS CLARIFICATION: y?]", encoding="utf-8"
        )
        proc = run_gate_subprocess(
            "gate_clarification.py",
            {"cwd": str(self.root), "prompt": "/icm:implement x"},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("y?", proc.stderr)

    def test_gate_spec_edit(self) -> None:
        proc = run_gate_subprocess(
            "gate_spec_edit.py",
            {
                "cwd": str(self.root),
                "tool_input": {
                    "file_path": str(
                        self.root / "specs" / "commands" / "find.md"
                    )
                },
            },
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(
            specific_output(proc).get("permissionDecision"), "ask"
        )

    def test_gate_output_naming(self) -> None:
        stage01 = (
            self.root
            / "ICM"
            / "process-plan"
            / "stages"
            / "01-specification"
            / "output"
        )
        proc = run_gate_subprocess(
            "gate_output_naming.py",
            {
                "cwd": str(self.root),
                "tool_input": {"file_path": str(stage01 / "notes.md")},
            },
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(
            specific_output(proc).get("permissionDecision"), "deny"
        )

    def test_gate_plan_frontmatter(self) -> None:
        write_plan(self.root, "bogus", status="bogus")
        proc = run_gate_subprocess(
            "gate_plan_frontmatter.py",
            {
                "cwd": str(self.root),
                "tool_input": {
                    "file_path": str(self.root / "plans" / "bogus.md")
                },
            },
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn(
            "bogus", specific_output(proc).get("additionalContext", "")
        )

    def test_gate_spec_frontmatter(self) -> None:
        (self.root / "specs" / "commands").mkdir(parents=True)
        (self.root / "specs" / "commands" / "find.md").write_text(
            "# Command: acme find", encoding="utf-8"
        )
        proc = run_gate_subprocess(
            "gate_spec_frontmatter.py",
            {
                "cwd": str(self.root),
                "tool_input": {
                    "file_path": str(
                        self.root / "specs" / "commands" / "find.md"
                    )
                },
            },
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn(
            "no YAML frontmatter block",
            specific_output(proc).get("additionalContext", ""),
        )

    def test_gate_spec_coverage(self) -> None:
        (self.root / "specs" / "commands").mkdir(parents=True)
        (self.root / "specs" / "commands" / "orphan.md").write_text(
            "# spec", encoding="utf-8"
        )
        proc = run_gate_subprocess(
            "gate_spec_coverage.py",
            {"cwd": str(self.root), "stop_hook_active": False},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("orphan.md", proc.stderr)

    def test_gate_closeout(self) -> None:
        write_plan(self.root, "closing", status="done", pr="")
        proc = run_gate_subprocess(
            "gate_closeout.py",
            {"cwd": str(self.root), "stop_hook_active": False},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("pr:", proc.stderr)

    def test_preflight(self) -> None:
        proc = run_gate_subprocess(
            "preflight.py", {"cwd": str(self.root), "source": "startup"}
        )
        self.assertEqual(proc.returncode, 0)
        out = specific_output(proc)
        self.assertEqual(out.get("hookEventName"), "SessionStart")
        self.assertIn("gates armed", out.get("additionalContext", ""))


if __name__ == "__main__":
    unittest.main()

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

import json
import os
import unittest

from .support import (
    TempDirCase,
    run_gate_subprocess,
    run_gate_subprocess_bytes,
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


class StreamEncodingContractTests(TempDirCase):
    """Issue #14: the event and message channels are UTF-8 byte contracts.

    Only a real spawn exercises real stream encoding - the in-process
    layer's patched streams cannot. Each test pins the child's would-be
    locale streams to a deliberately hostile codepage via
    `PYTHONIOENCODING`, so the rows fail on the pre-fix code on every
    platform rather than only under a mismatched OS codepage.
    """

    def test_stdin_decodes_raw_utf8_despite_the_codepage(self) -> None:
        # Feed raw UTF-8 non-ASCII bytes exactly as the hook host does
        # (`ensure_ascii=False`, so the wire really carries them). Under the
        # old text-mode `json.load`, cp1252 decodes them into mojibake
        # without raising and the deny reason names a path that exists
        # nowhere; `read_event` now reads `sys.stdin.buffer` as UTF-8.
        file_path = self.root / "specs" / "commands" / "naïve-café.md"
        event = {
            "cwd": str(self.root),
            "tool_input": {"file_path": str(file_path)},
        }
        proc = run_gate_subprocess_bytes(
            "gate_spec_edit.py",
            json.dumps(event, ensure_ascii=False).encode("utf-8"),
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        self.assertEqual(proc.returncode, 0)
        out = specific_output(proc.stdout.decode("utf-8"))
        self.assertEqual(out.get("permissionDecision"), "ask")
        self.assertIn(
            "specs/commands/naïve-café.md",
            out.get("permissionDecisionReason", ""),
        )

    def test_stderr_carries_utf8_despite_the_codepage(self) -> None:
        # An ASCII-pinned stderr made a non-ASCII deny message a
        # `UnicodeEncodeError` (a traceback and the wrong exit code) before
        # `_common` reconfigured the stream to UTF-8 at import time.
        outdir = (
            self.root
            / "ICM"
            / "process-plan"
            / "stages"
            / "01-specification"
            / "output"
        )
        (outdir / "x-spec.md").write_text(
            "[NEEDS CLARIFICATION: café?]", encoding="utf-8"
        )
        event = {"cwd": str(self.root), "prompt": "/icm:implement x"}
        proc = run_gate_subprocess_bytes(
            "gate_clarification.py",
            json.dumps(event).encode("utf-8"),
            env={**os.environ, "PYTHONIOENCODING": "ascii"},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("café?", proc.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()

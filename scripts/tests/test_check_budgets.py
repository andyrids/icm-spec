"""Companion tests for `check_budgets.py`; the program is unchanged.

NOTE: `tiktoken` is a `uv` inline-script dependency of the program, not
of this suite - importing it here would make the whole suite fail where
only `just test-budgets` should. Both cases go through one real
`uv run --script` spawn each, exactly as the Justfile deploys it.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import shutil
import subprocess
import unittest
from pathlib import Path

from .support import TempDirCase

SCRIPT = Path(__file__).resolve().parent / "check_budgets.py"

BUDGETED = """---
maximum-context-tokens: {budget}
---

{body}
"""


@unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
class CheckBudgetsTests(TempDirCase):
    scaffold_icm = False

    def _run(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--script",
                str(SCRIPT),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_a_breached_budget_fails_and_is_named(self) -> None:
        (self.root / "over.md").write_text(
            BUDGETED.format(budget=10, body="word " * 200),
            encoding="utf-8",
        )
        (self.root / "fine.md").write_text(
            BUDGETED.format(budget=500, body="short"), encoding="utf-8"
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("OVER", proc.stdout)
        self.assertIn("over.md", proc.stdout)
        self.assertNotIn("fine.md", proc.stdout)

    def test_compliant_and_undeclared_files_pass(self) -> None:
        # A file with no `maximum-context-tokens` line is unbudgeted by
        # contract (specs), not over budget.
        (self.root / "fine.md").write_text(
            BUDGETED.format(budget=500, body="short"), encoding="utf-8"
        )
        (self.root / "unbudgeted.md").write_text(
            "word " * 500, encoding="utf-8"
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("1 budgeted documents checked", proc.stdout)


if __name__ == "__main__":
    unittest.main()

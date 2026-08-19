"""Layer B: `gate_plan_frontmatter.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_plan_frontmatter

from .support import (
    TempDirCase,
    call_gate_main,
    specific_output,
    write_bytes,
    write_plan,
)


class GatePlanFrontmatterTests(TempDirCase):
    def _event(self, slug: str) -> dict:
        return {
            "cwd": str(self.root),
            "tool_input": {
                "file_path": str(self.root / "plans" / f"{slug}.md")
            },
        }

    def _context(self, slug: str) -> str:
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event(slug)
        )
        return specific_output(out).get("additionalContext", "")

    def _real_spec(self) -> None:
        (self.root / "specs" / "commands").mkdir(
            parents=True, exist_ok=True
        )
        (self.root / "specs" / "commands" / "real.md").write_text(
            "# spec", encoding="utf-8"
        )

    def test_flags_an_invalid_status(self) -> None:
        """Check that the gate flags a plan with an invalid status."""

        write_plan(self.root, "bogus", status="bogus")
        self.assertIn("bogus", self._context("bogus"))

    def test_flags_an_unresolvable_specs_entry(self) -> None:
        """Check the gate flags a plan with an invalid specs entry."""

        write_plan(
            self.root, "dangling", specs="\n  - specs/commands/missing.md"
        )
        self.assertIn("missing.md", self._context("dangling"))

    def test_flags_an_unresolvable_authors_entry(self) -> None:
        """Check the gate flags a plan with an invalid authors entry."""

        write_plan(
            self.root,
            "dangling-author",
            authors="\n  - specs/behaviors/ghost.md",
        )
        self.assertIn("ghost.md", self._context("dangling-author"))

    def test_flags_a_spec_claimed_by_both_fields(self) -> None:
        """Check the gate flags plans with a spec in `specs:` & `authors:`."""

        self._real_spec()
        write_plan(
            self.root,
            "both",
            specs="\n  - specs/commands/real.md",
            authors="\n  - specs/commands/real.md",
        )
        self.assertIn("both specs: and authors:", self._context("both"))

    def test_flags_a_missing_layer4_hierarchy_key(self) -> None:
        """Check the gate flags a plan with no `context-hierarchy:` key."""

        (self.root / "plans").mkdir(exist_ok=True)
        (self.root / "plans" / "flat.md").write_text(
            "---\nstatus: planned\nspecs: []\nauthors: []\npr:\n---\n"
            "\n# Plan: no hierarchy\n",
            encoding="utf-8",
        )
        self.assertIn(
            "context-hierarchy: is missing", self._context("flat")
        )

    def test_passes_a_valid_plan(self) -> None:
        """Check the gate passes a plan with a valid status & specs."""

        self._real_spec()
        write_plan(self.root, "valid", specs="\n  - specs/commands/real.md")
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("valid")
        )
        self.assertEqual(out.strip(), "")

    def test_passes_a_spec_authoring_plan(self) -> None:
        """Check the gate passes a plan with a valid status & authors."""

        self._real_spec()
        write_plan(
            self.root, "authoring", authors="\n  - specs/commands/real.md"
        )
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("authoring")
        )
        self.assertEqual(out.strip(), "")

    def test_a_non_utf8_plan_degrades_to_no_verdict(self) -> None:
        """Check that a non-UTF-8 plan does not crash the gate.
        
        NOTE: This test uses a non-UTF-8 encoded plan."""

        write_bytes(
            self.root, "plans/binary.md", b"---\nstatus: caf\xe9\n---\n"
        )
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("binary")
        )
        self.assertEqual(out.strip(), "")
        write_plan(self.root, "bogus", status="bogus")
        self.assertIn("bogus", self._context("bogus"))

    def test_an_embedded_nul_path_degrades_to_no_verdict(self) -> None:
        """Check a plan with an embedded NUL in its path does not crash.

        NOTE: This test uses a plan with an embedded NUL in its path.
        """

        rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("bad\x00plan")
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")
        write_plan(self.root, "bogus", status="bogus")
        self.assertIn("bogus", self._context("bogus"))

    def test_a_malformed_tool_input_degrades_to_silence(self) -> None:
        """Check that a malformed `tool_input` does not crash the gate."""

        for tool_input in (None, "file_path", ["/x/y.md"]):
            with self.subTest(tool_input=tool_input):
                rc, out, _err = call_gate_main(
                    gate_plan_frontmatter,
                    {"cwd": str(self.root), "tool_input": tool_input},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(out.strip(), "")
        write_plan(self.root, "bogus", status="bogus")
        self.assertIn("bogus", self._context("bogus"))

    def test_ignores_plans_readme(self) -> None:
        """Check that the gate ignores a plans/README.md file."""

        (self.root / "plans").mkdir(exist_ok=True)
        (self.root / "plans" / "README.md").write_text(
            "# Plans", encoding="utf-8"
        )
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("README")
        )
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()

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
        write_plan(self.root, "bogus", status="bogus")
        self.assertIn("bogus", self._context("bogus"))

    def test_flags_an_unresolvable_specs_entry(self) -> None:
        write_plan(
            self.root, "dangling", specs="\n  - specs/commands/missing.md"
        )
        self.assertIn("missing.md", self._context("dangling"))

    def test_flags_an_unresolvable_authors_entry(self) -> None:
        write_plan(
            self.root,
            "dangling-author",
            authors="\n  - specs/behaviors/ghost.md",
        )
        self.assertIn("ghost.md", self._context("dangling-author"))

    def test_flags_a_spec_claimed_by_both_fields(self) -> None:
        # A spec whose code the plan brings into conformance belongs in
        # specs: alone - claiming both blurs the distinction the coverage
        # gate relies on.
        self._real_spec()
        write_plan(
            self.root,
            "both",
            specs="\n  - specs/commands/real.md",
            authors="\n  - specs/commands/real.md",
        )
        self.assertIn("both specs: and authors:", self._context("both"))

    def test_flags_a_missing_layer4_hierarchy_key(self) -> None:
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
        self._real_spec()
        write_plan(self.root, "valid", specs="\n  - specs/commands/real.md")
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("valid")
        )
        self.assertEqual(out.strip(), "")

    def test_passes_a_spec_authoring_plan(self) -> None:
        # `authors:` with `specs: []` is the correct shape for a plan
        # that writes a spec without changing behaviour.
        self._real_spec()
        write_plan(
            self.root, "authoring", authors="\n  - specs/commands/real.md"
        )
        _rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("authoring")
        )
        self.assertEqual(out.strip(), "")

    def test_a_non_utf8_plan_degrades_to_no_verdict(self) -> None:
        # `UnicodeDecodeError` is a `ValueError` that `except OSError`
        # never caught (issue #8): an undecodable plan crashed a
        # PostToolUse hook that cannot block anyway. It must degrade to
        # silence - and the gate itself must stay standing, so the next
        # event against a readable plan still gets its verdict.
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
        # The residue of issue #8 (issue #17): a NUL in `file_path`
        # passes `resolve()` and `relative_to()` and only raises inside
        # `read_text`, as a `ValueError` that is NOT a
        # `UnicodeDecodeError` - so the guard narrowed to
        # `(OSError, UnicodeDecodeError)` still crashed the hook. It must
        # degrade to silence - and the gate itself must stay standing, so
        # the next event against a readable plan still gets its verdict.
        rc, out, _err = call_gate_main(
            gate_plan_frontmatter, self._event("bad\x00plan")
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")
        write_plan(self.root, "bogus", status="bogus")
        self.assertIn("bogus", self._context("bogus"))

    def test_a_malformed_tool_input_degrades_to_silence(self) -> None:
        # `read_event` only guards the top-level event (issue #15): a
        # present-but-non-dict `tool_input` crashed the gate with an
        # `AttributeError` on the chained `.get`. It must degrade to
        # exit 0 with no verdict instead - and the gate must stay
        # standing, so the next well-formed event still gets its verdict.
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

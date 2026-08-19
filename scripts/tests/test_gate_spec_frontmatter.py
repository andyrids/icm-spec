"""Layer B: `gate_spec_frontmatter.main()` in-process, real tempdir.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import unittest

import gate_spec_frontmatter

from .support import TempDirCase, call_gate_main, specific_output, write_bytes

VALID = """---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [find, cli]
---

# Command: acme find"""


class GateSpecFrontmatterTests(TempDirCase):
    def _write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    def _event(self, rel: str) -> dict:
        return {
            "cwd": str(self.root),
            "tool_input": {"file_path": str(self.root / rel)},
        }

    def _context(self, rel: str) -> str:
        _rc, out, _err = call_gate_main(
            gate_spec_frontmatter, self._event(rel)
        )
        return specific_output(out).get("additionalContext", "")

    def _silence(self, rel: str) -> str:
        _rc, out, _err = call_gate_main(
            gate_spec_frontmatter, self._event(rel)
        )
        return out.strip()

    def test_flags_a_spec_with_no_frontmatter_block(self) -> None:
        """Check a spec with no frontmatter block is flagged."""

        self._write("specs/commands/find.md", "# Command: acme find")
        context = self._context("specs/commands/find.md")
        self.assertIn("no YAML frontmatter block", context)
        self.assertIn("specs/README.md", context)

    def test_flags_a_missing_layer3_hierarchy_key(self) -> None:
        """Check a spec missing the Layer 3 hierarchy key is flagged."""

        self._write(
            "specs/commands/find.md",
            "---\ncontext-hierarchy-role: Reference material\n"
            "immutable: false\n---\n\n# Command: acme find",
        )
        self.assertIn(
            "context-hierarchy: is missing",
            self._context("specs/commands/find.md"),
        )

    def test_flags_a_wrong_immutable_value(self) -> None:
        """Check a spec with the wrong `immutable` value is flagged."""

        self._write(
            "specs/commands/find.md", VALID.replace("false", "true")
        )
        self.assertIn(
            "immutable: is 'true', expected 'false'",
            self._context("specs/commands/find.md"),
        )

    def test_flags_a_layer_4_role_pasted_onto_a_spec(self) -> None:
        """Check a spec with a Layer 4 role pasted onto it is flagged."""

        self._write(
            "specs/commands/find.md",
            VALID.replace("Reference material", "Working artifact"),
        )
        self.assertIn(
            "context-hierarchy-role: is 'Working artifact'",
            self._context("specs/commands/find.md"),
        )

    def test_passes_a_valid_spec(self) -> None:
        self._write("specs/commands/find.md", VALID)
        self.assertEqual(self._silence("specs/commands/find.md"), "")

    def test_passes_a_valid_spec_carrying_no_tags(self) -> None:
        """Check a spec with no `tags` key is not flagged."""

        lines = [
            line for line in VALID.splitlines() if not line.startswith("tags:")
        ]
        self._write("specs/commands/find.md", "\n".join(lines))
        self.assertEqual(self._silence("specs/commands/find.md"), "")

    def test_judges_a_flat_principles_file(self) -> None:
        """Check a flat principles file is judged correctly."""

        self._write("specs/principles.md", "# Principles")
        self.assertIn(
            "no YAML frontmatter block", self._context("specs/principles.md")
        )

    def test_passes_a_valid_flat_principles_file(self) -> None:
        """Check a flat principles file with valid frontmatter passess."""

        self._write("specs/principles.md", VALID)
        self.assertEqual(self._silence("specs/principles.md"), "")

    def test_judges_a_deeply_nested_spec(self) -> None:
        """Check a deeply nested spec is judged correctly."""

        self._write("specs/mcp/tools/inspect.md", "# Tool: inspect")
        self.assertIn(
            "no YAML frontmatter block",
            self._context("specs/mcp/tools/inspect.md"),
        )

    def test_ignores_specs_readme(self) -> None:
        """Check a specs README is ignored."""

        self._write("specs/README.md", "# Specifications")
        self.assertEqual(self._silence("specs/README.md"), "")

    def test_a_malformed_tool_input_degrades_to_silence(self) -> None:
        """Check a malformed `tool_input` degrades to silence."""

        for tool_input in (None, "file_path", ["/x/y.md"]):
            with self.subTest(tool_input=tool_input):
                rc, out, _err = call_gate_main(
                    gate_spec_frontmatter,
                    {"cwd": str(self.root), "tool_input": tool_input},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(out.strip(), "")
        self._write("specs/commands/find.md", "# Command: acme find")
        self.assertIn(
            "no YAML frontmatter block",
            self._context("specs/commands/find.md"),
        )

    def test_a_non_utf8_spec_degrades_to_no_verdict(self) -> None:
        """Check a non-UTF-8 spec degrades to no verdict."""

        write_bytes(
            self.root,
            "specs/commands/binary.md",
            b"---\ncontext-hierarchy: caf\xe9\n---\n",
        )
        self.assertEqual(self._silence("specs/commands/binary.md"), "")
        self._write("specs/commands/find.md", "# Command: acme find")
        self.assertIn(
            "no YAML frontmatter block",
            self._context("specs/commands/find.md"),
        )

    def test_an_embedded_nul_path_degrades_to_no_verdict(self) -> None:
        """Check a spec with an embedded NUL in its path degrades."""

        self.assertEqual(
            self._silence("specs/commands/bad\x00spec.md"), ""
        )
        self._write("specs/commands/find.md", "# Command: acme find")
        self.assertIn(
            "no YAML frontmatter block",
            self._context("specs/commands/find.md"),
        )


if __name__ == "__main__":
    unittest.main()

"""Companion tests for `check_manifest.py`; the program is unchanged.

The three version statements are fixture files here, so every drift case
is reachable - `just test-manifest` still runs the program against the
real repository.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import contextlib
import io
import json
import unittest
from unittest import mock

from . import check_manifest
from .support import TempDirCase

VERSION = "2.3.4"


class CheckManifestTests(TempDirCase):
    scaffold_icm = False

    def _run(
        self,
        plugin: dict | None = None,
        marketplace: dict | None = None,
        changelog: str | None = None,
    ) -> tuple[int, str]:
        """Run `main()` against fixture files, agreeing by default."""
        # Explicit None checks: `{}` is a meaningful fixture (a manifest
        # declaring no version) and must not fall back to the default.
        if plugin is None:
            plugin = {"version": VERSION}
        if marketplace is None:
            marketplace = {"plugins": [{"name": "icm"}]}
        if changelog is None:
            changelog = f"## [{VERSION}] - 2026-01-01\n"
        files = {
            "plugin.json": json.dumps(plugin),
            "marketplace.json": json.dumps(marketplace),
            "CHANGELOG.md": changelog,
        }
        for name, text in files.items():
            (self.root / name).write_text(text, encoding="utf-8")
        with (
            mock.patch.object(
                check_manifest, "PLUGIN", self.root / "plugin.json"
            ),
            mock.patch.object(
                check_manifest,
                "MARKETPLACE",
                self.root / "marketplace.json",
            ),
            mock.patch.object(
                check_manifest, "CHANGELOG", self.root / "CHANGELOG.md"
            ),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            rc = check_manifest.main()
        return rc, out.getvalue()

    def test_agreement_everywhere_passes(self) -> None:
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("0 in disagreement", out)

    def test_an_unreleased_top_heading_is_accepted(self) -> None:
        # In-progress work is never blocked: the CHANGELOG may lead with
        # [unreleased] until the release heading lands with the bump.
        rc, _out = self._run(
            changelog=f"## [unreleased]\n\n## [{VERSION}] - 2026-01-01\n"
        )
        self.assertEqual(rc, 0)

    def test_drift_table(self) -> None:
        rows: list[tuple[str, dict, str]] = [
            (
                "plugin.json declares no version",
                {"plugin": {}},
                "authoritative field is empty",
            ),
            (
                "marketplace has no icm entry",
                {"marketplace": {"plugins": []}},
                "no entry named icm",
            ),
            (
                # plugin.json wins silently, so a marketplace version can
                # mask a bump and the release reaches nobody.
                "marketplace entry declares a version",
                {
                    "marketplace": {
                        "plugins": [{"name": "icm", "version": "9.9.9"}]
                    }
                },
                "masks it silently",
            ),
            (
                "CHANGELOG has no release heading",
                {"changelog": "# Changelog\n"},
                "no release heading",
            ),
            (
                "CHANGELOG top heading disagrees",
                {"changelog": "## [9.9.9] - 2026-01-01\n"},
                f"is [9.9.9], plugin.json says {VERSION}",
            ),
        ]
        for name, kwargs, expected in rows:
            with self.subTest(name):
                rc, out = self._run(**kwargs)
                self.assertEqual(rc, 1)
                self.assertIn("DRIFT", out)
                self.assertIn(expected, out)


if __name__ == "__main__":
    unittest.main()

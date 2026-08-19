"""Unit test package for the ICM gate scripts and check helpers.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys
from pathlib import Path


_SCRIPTS = str(Path(__file__).resolve().parent.parent)
"""A pathlib.Path to /scripts, for flat imports of gate & helper functions.

NOTE: Discovery with `-t scripts` already puts `scripts/` on sys.path; the
dotted single-test invocation from the repo root does not, hence this
bootstrap.
"""

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

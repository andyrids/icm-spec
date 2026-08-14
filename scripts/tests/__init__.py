"""Unit test package for the ICM gate scripts and check helpers.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import sys
from pathlib import Path

# The gates import `_common` flat, so the suite must resolve it the same
# way. Discovery with `-t scripts` already puts `scripts/` on sys.path;
# the dotted single-test invocation from the repo root does not, hence
# this bootstrap. Load-bearing for discovery too: `start_dir` differs
# from `top_level_dir`, so unittest requires this file to exist.
_SCRIPTS = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

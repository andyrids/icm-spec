"""Shared fixtures and drivers for the ICM gate test suite.

Three layers use this module: pure-function tests need nothing here,
in-process tests drive a gate's `main()` through `call_gate_main` inside
a `TempDirCase` tempdir, and the process-contract tests spawn a real
interpreter through `run_gate_subprocess`.

Run: python -m unittest discover -s scripts/tests -t scripts

License:
    SPDX-License-Identifier: Apache-2.0
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent

# Full git isolation for every fixture, in-process gate call and spawned
# script. A contributor's global config is a fixture ingredient nobody
# ordered: `status.renames=false` would silently downgrade every R row to
# D+A and test nothing, `core.autocrlf` rewrites the bytes under test,
# `commit.gpgsign` can hang a commit on a missing key. `GIT_CONFIG_GLOBAL`
# pointed at the null device suppresses global and system config alike;
# the `GIT_CONFIG_*` triplets re-add only what the fixtures rely on.
_GIT_ISOLATION = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "icm-test",
    "GIT_AUTHOR_EMAIL": "test@test",
    "GIT_COMMITTER_NAME": "icm-test",
    "GIT_COMMITTER_EMAIL": "test@test",
    "GIT_CONFIG_COUNT": "4",
    "GIT_CONFIG_KEY_0": "init.defaultBranch",
    "GIT_CONFIG_VALUE_0": "main",
    "GIT_CONFIG_KEY_1": "core.autocrlf",
    "GIT_CONFIG_VALUE_1": "false",
    "GIT_CONFIG_KEY_2": "commit.gpgsign",
    "GIT_CONFIG_VALUE_2": "false",
    "GIT_CONFIG_KEY_3": "status.renames",
    "GIT_CONFIG_VALUE_3": "true",
}

PLAN_TEMPLATE = """---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: {status}
depends: []
specs: {specs}
authors: {authors}
issues: []
pr: {pr}
---

# Plan: test fixture

## Scope

Fixture.

## Validation

{validation}

## Notes

{notes}
"""


def make_repo(root: Path) -> None:
    """Initialise a git repository at `root`."""
    subprocess.run(
        ["git", "init", "-q"], cwd=root, check=True, capture_output=True
    )


def make_icm_tree(root: Path) -> None:
    """The `ICM/` marker `/icm:init` writes; every gate no-ops without it."""
    (
        root
        / "ICM"
        / "process-plan"
        / "stages"
        / "01-specification"
        / "output"
    ).mkdir(parents=True, exist_ok=True)


def git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    """Run one git command in `root`.

    NOTE: `git_commit_all` hardcodes add+commit; the porcelain matrix needs
    mv, checkout and merge - and `merge` exits 1 on the conflict it is
    there to produce, hence `check` is a parameter. Identity and config
    come from `_GIT_ISOLATION` in the process environment, which also
    reaches the `git status` the gates themselves run.

    Args:
        root: The repository to run in.
        *args: The git subcommand and its arguments.
        check: Raise on a non-zero exit when True.

    Returns:
        The completed process, with text output captured.
    """
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


def git_commit_all(root: Path) -> None:
    """Stage and commit everything in `root` as one fixture commit."""
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture")


def porcelain(root: Path, subdir: str) -> list[str]:
    """The newline-porcelain v1 lines for `subdir` - an independent oracle.

    Deliberately NOT the invocation the gates read: `git_pending_paths`
    moved to `-z` NUL records (issue #6), and keeping this human-readable
    form separate is what lets the non-ASCII rows assert git's C-quoted
    line first and the gate's clean verdict second. Every matrix row
    asserts the code its fixture actually reached. A fixture that degrades
    quietly - a rename landing as D+A, an edit git calls racily clean -
    turns a regression test green for the wrong reason, and the status
    column is the thing under test.

    Args:
        root: The repository to inspect.
        subdir: The pathspec to limit the status to.

    Returns:
        The porcelain v1 output lines, one per pending path.
    """
    return git(
        root, "status", "--porcelain", "-uall", "--", subdir
    ).stdout.splitlines()


def case_repo(root: Path, name: str) -> Path:
    """A fresh ICM repo per matrix row, inside the test's own tempdir.

    The rows share no state deliberately: the gate blocks on ANY uncovered
    spec, so an orphan left by one row would keep every later row blocked
    and the guard rows would assert nothing.

    Args:
        root: The tempdir to create the repository under.
        name: The row's subdirectory name.

    Returns:
        The new repository root.
    """
    sub = root / name
    sub.mkdir()
    make_repo(sub)
    make_icm_tree(sub)
    return sub


def write_spec(root: Path, name: str, text: str = "# spec") -> None:
    """Mirror of `write_plan` for the coverage matrix's `specs/**` files."""
    path = root / "specs" / "commands" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def write_plan(
    root: Path,
    slug: str,
    status: str = "planned",
    specs: str = "[]",
    authors: str = "[]",
    pr: str = "",
    validation: str = "- [x] done",
    notes: str = "",
) -> None:
    """Write a plan file with the given frontmatter and body."""
    (root / "plans").mkdir(exist_ok=True)
    (root / "plans" / f"{slug}.md").write_text(
        PLAN_TEMPLATE.format(
            status=status,
            specs=specs,
            authors=authors,
            pr=pr,
            validation=validation,
            notes=notes,
        ),
        encoding="utf-8",
    )


def write_bytes(root: Path, rel: str, data: bytes) -> None:
    """Write raw bytes at `rel` under `root`, creating parent directories.

    NOTE: The suite's only route to a non-UTF-8 fixture (issue #8):
    `write_plan` and `write_spec` encode UTF-8 by construction, and the
    defect class is exactly the file that does not - a latin-1 byte that
    `read_text(encoding="utf-8")` turns into a `UnicodeDecodeError` no
    `except OSError` catches.

    Args:
        root: The fixture tree root.
        rel: The forward-slash path to write, relative to `root`.
        data: The literal bytes to write, no encoding step.
    """
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def utf8_stdin(text: str) -> io.TextIOWrapper:
    """A stdin stand-in whose `.buffer` holds `text` as UTF-8 bytes.

    NOTE: `read_event` reads `sys.stdin.buffer` (issue #14), which a bare
    `io.StringIO` does not have - every in-process stdin patch goes through
    here so the stand-in stays shaped like a real text stream (`.read()`
    still works) while exposing the byte layer the production code reads.

    Args:
        text: The stdin payload, encoded to UTF-8 on the way in.

    Returns:
        A text wrapper over a `BytesIO` of the UTF-8-encoded payload.
    """
    return io.TextIOWrapper(
        io.BytesIO(text.encode("utf-8")), encoding="utf-8"
    )


def call_gate_main(
    module: ModuleType, event: dict
) -> tuple[int, str, str]:
    """Drive one gate's `main()` in-process against a hook event.

    NOTE: `mock.patch` for stdin because `contextlib` has no
    `redirect_stdin`. Patching the `sys` streams works because
    `read_event` and `emit` resolve them at call time - patching
    `_common.read_event` would not reach the gates, which bind it at
    import time.

    Args:
        module: The imported gate module.
        event: The hook event to serialise onto stdin.

    Returns:
        `(returncode, stdout, stderr)` exactly as a hook runner sees them.
    """
    with (
        mock.patch("sys.stdin", utf8_stdin(json.dumps(event))),
        contextlib.redirect_stdout(io.StringIO()) as out,
        contextlib.redirect_stderr(io.StringIO()) as err,
    ):
        rc = module.main()
    return rc, out.getvalue(), err.getvalue()


def run_gate_subprocess(
    script: str, event: dict
) -> subprocess.CompletedProcess:
    """Spawn one gate script as the hook runner deploys it.

    Args:
        script: The filename under `scripts/`.
        event: The hook event to serialise onto stdin.

    Returns:
        The completed process, with text output captured.
    """
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_gate_subprocess_bytes(
    script: str, stdin: bytes, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """Spawn one gate script with raw bytes on stdin, no text layer.

    NOTE: `run_gate_subprocess` serialises through `text=True`, which
    encodes stdin in the parent's locale - exactly the layer issue #14
    removes from the gates. The stream-encoding regression tests must
    control the bytes on the wire and read the bytes coming back, so this
    variant passes `stdin` verbatim and captures bytes, with `env`
    overridable to pin the child's would-be locale streams (e.g.
    `PYTHONIOENCODING`) to the codepage the defect needs.

    Args:
        script: The filename under `scripts/`.
        stdin: The literal bytes to feed on stdin, no encoding step.
        env: The child environment, or None to inherit the parent's.

    Returns:
        The completed process, with byte output captured.
    """
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        input=stdin,
        capture_output=True,
        env=env,
        timeout=30,
    )


def specific_output(
    result: subprocess.CompletedProcess | str,
) -> dict:
    """Parse the `hookSpecificOutput` object from a gate's stdout.

    Args:
        result: A completed process, or the captured stdout string.

    Returns:
        The `hookSpecificOutput` mapping, or {} when there is none.
    """
    stdout = result if isinstance(result, str) else result.stdout
    try:
        return json.loads(stdout)["hookSpecificOutput"]
    except (json.JSONDecodeError, KeyError):
        return {}


class TempDirCase(unittest.TestCase):
    """One isolated tempdir per test method, with git env isolation.

    NOTE: `addCleanup` rather than `tearDown` so a `setUp` that fails
    partway still cleans up what it already built.
    `ignore_cleanup_errors` because git leaves read-only objects under
    `.git/objects` and Windows teardown fails on them without it.
    """

    scaffold_icm = True  # subclasses that must NOT have ICM/ set False
    scaffold_git = False  # subclasses needing a repo at self.root set True

    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ, _GIT_ISOLATION)
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        if self.scaffold_icm:
            make_icm_tree(self.root)
        if self.scaffold_git:
            make_repo(self.root)

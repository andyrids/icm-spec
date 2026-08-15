"""Shared helpers for the ICM gate hook scripts.

Every gate reads one hook event as JSON on stdin and answers on stdout (JSON
`hookSpecificOutput`) or via exit code. Exit 2 is reserved for hard blocks;
anything unexpected degrades to exit 0 so a broken gate never wedges a session.

License:
    SPDX-License-Identifier: Apache-2.0
"""

import json
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path, PurePosixPath
from typing import Any

STATUS_ENUM = {"planned", "in-progress", "done", "blocked", "cancelled"}

# The two plan frontmatter fields that answer Invariant 1. `specs` names
# conformance targets, `authors` names specs the plan writes without changing
# code - a distinction the coverage gate needs and stage 03 must not blur.
LIST_KEYS = ("specs", "authors")

# Layer 4 hierarchy keys every plan carries (AGENTS.md).
EXPECTED_HIERARCHY = {
    "context-hierarchy": "Layer 4",
    "context-hierarchy-role": "Working artifact",
    "immutable": "false",
}

SLUG_SUFFIX_BY_STAGE = {
    "01": "spec",
    "02": "code",
    "03": "test",
    "04": "docs",
}

# Porcelain v1 unmerged codes (git-status(1)). "DD", "DU" and "UD" carry a "D"
# and the delete guard in `git_pending_paths` would drop them anyway; naming the
# whole set makes "AA", "AU", "UA" and "UU" a decision rather than a side-effect
# of that guard. A conflicted path is a merge in motion, not work under review:
# the file holds conflict markers, `plans/` may itself be half-resolved, and the
# only honest next action is to resolve, not to edit frontmatter. Nothing
# escapes - once resolved and staged the same path presents as "A ", "AM" or
# "M " and is judged on the next Stop.
GIT_UNMERGED = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})


def read_event() -> dict[str, Any]:
    """Parse hook event JSON from STDIN.

    Returns:
        The parsed event, or an empty dict on failure.
    """
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def project_dir(event: dict[str, Any]) -> Path:
    """Get the current working directory."""
    return Path(event.get("cwd") or ".").resolve()


def is_icm_project(root: Path) -> bool:
    """Check if `root` has been scaffolded by `/icm:init`.

    Args:
        root: The project root directory.

    NOTE: `ICM/` is what `/icm:init` writes and what every stage skill reads.
    Its absence means there is no contract to enforce and the gate must stay
    silent.
    """
    return (root / "ICM").is_dir()


def relative_posix(file_path: str, root: Path) -> str | None:
    """Resolve a file path relative to the root directory.

    Args:
        file_path: The file path to resolve.
        root: The root directory to resolve against.

    Returns:
        The relative path with forward slashes, or None if the file is outside
        the root.
    """
    try:
        rel = Path(file_path).resolve().relative_to(root)
    except (ValueError, OSError):
        return None
    return str(PurePosixPath(rel))


def frontmatter_lines(text: str) -> list[str] | None:
    """Get the raw YAML frontmatter lines of a markdown document.

    Args:
        text: The markdown document as a string.

    Returns:
        The raw YAML frontmatter lines as a list of strings, or None if no
        frontmatter is found.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end].strip("\n").splitlines()


def _strip_comment(value: str) -> str:
    """Strip an inline comment from a scalar value.

    NOTE: Only a `#` outside a quoted region starts a comment. Splitting on
    the first `#` unconditionally truncated `"specs/a#b.md"` to `"specs/a`
    before `_unquote` could ever see the pair (issue #9) - so this runs
    first and must be quote-aware, tracking single- and double-quote state.
    An unterminated quote swallows the rest of the line, comment included,
    which leaves the author's typo intact for a gate to name rather than
    half-parsing it. Unquoted values behave exactly as before.

    Args:
        value: The scalar value as a string.

    Returns:
        The value with the inline comment stripped.
    """
    quote = ""
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#":
            return value[:index].strip()
    return value.strip()


def _unquote(value: str) -> str:
    """Strip one matching pair of surrounding quotes from a scalar value.

    NOTE: Deliberately conservative (issue #9): exactly one pair, and only
    when both ends match, so an internal apostrophe (`it's-a-file.md`) and
    an unterminated quote are left verbatim - a value the parser cannot
    read cleanly should surface in a gate's message as written, not be
    half-corrected into a path that exists nowhere.

    Args:
        value: The comment-stripped scalar value as a string.

    Returns:
        The value with its surrounding quote pair removed, or unchanged.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_plan_frontmatter(text: str) -> dict[str, Any] | None:
    """Extract metadata from plan frontmatter.

    NOTE: Frontmatter-only by construction - the body is never scanned, so
    prose mentioning a spec can never register as coverage.

    Args:
        text: The markdown document as a string.

    Returns:
        A dict with keys "status", "pr", the `LIST_KEYS` (each a list of
        strings) and the `EXPECTED_HIERARCHY` keys, or None if no frontmatter
        is found.
    """
    lines = frontmatter_lines(text)
    if lines is None:
        return None
    result: dict[str, Any] = {"status": None, "pr": None}
    result.update({key: [] for key in LIST_KEYS})
    result.update(dict.fromkeys(EXPECTED_HIERARCHY))
    list_key: str | None = None
    for line in lines:
        stripped = line.strip()
        if line.startswith((" ", "\t")):
            if list_key and stripped.startswith("- "):
                result[list_key].append(
                    _unquote(_strip_comment(stripped[2:]))
                )
            continue
        list_key = None
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        # Unquoted at every site a value is read (issue #9): quoting a value
        # is ordinary YAML, and a surviving quote character breaks every
        # comparison downstream - a coverage key that matches no `git status`
        # payload, a `status: "done"` off the enum. Here rather than in
        # `plan_spec_paths`, because `gate_plan_frontmatter` iterates the
        # parsed lists directly and must see the same bare values.
        value = _unquote(_strip_comment(value))
        if key in LIST_KEYS:
            if value.startswith("[") and value != "[]":
                inner = value.strip("[]")
                result[key] = [
                    _unquote(v.strip())
                    for v in inner.split(",")
                    if v.strip()
                ]
            else:
                list_key = key
        elif key in {"status", "pr", *EXPECTED_HIERARCHY}:
            result[key] = value or None
    return result


def plan_spec_paths(meta: dict[str, list[str]]) -> set[str]:
    """Every spec path a plan claims, across both coverage fields.

    NOTE: `specs` and `authors` answer different questions - conformance
    versus authorship - but Invariant 1 asks only whether some plan owns the
    spec at all, and either answer means yes.

    Args:
        meta: A parsed plan frontmatter mapping.

    Returns:
        The union of both fields, with backslashes normalised.
    """
    return {
        spec.replace("\\", "/")
        for key in LIST_KEYS
        for spec in meta.get(key, [])
    }


def iter_plans(root: Path) -> Generator[tuple[Path, str], Any, None]:
    """Yield path and content of every plan document.

    NOTE: Excludes `README.md` and ignores unreadable files, so a broken plan
    never wedges the gate. Unreadable includes undecodable:
    `UnicodeDecodeError` is a `ValueError`, which `except OSError` never
    caught, so one non-UTF-8 plan aborted the generator out of the caller's
    loop and stopped every other plan being judged (issue #8).

    Args:
        root: The project root directory.

    Yields:
        Tuples of `(path, text)` for each plan file.
    """
    plans = root / "plans"
    if not plans.is_dir():
        return
    for path in sorted(plans.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def git_pending_paths(root: Path, subdir: str) -> list[tuple[str, str]]:
    """Get uncommitted `(status, path)` pairs under `subdir`.

    NOTE: Returns [] when git is unavailable or the directory is not a
    repository - the gates only reason about work in flight and no repository
    means no verdict rather than a crash.

    Args:
        root: The project root directory.
        subdir: The subdirectory to check for uncommitted changes.

    Returns:
        A list of `(status, path)` pairs for uncommitted files under `subdir`.
        `status` is the raw two-character porcelain v1 column - index state
        then working-tree state, spaces preserved. It is positional: callers
        test `status[0]` or `status[1]` and never `status.strip()`, which
        collapses "A " and "AM" onto different strings and silently drops the
        second. `path` is the file exactly as it exists in the working tree,
        relative with `/` separators - `-z` output carries no quoting for the
        parse to undo (issue #6). For a rename or copy git emits the
        destination record first with the origin as the following NUL field,
        and only the destination is returned, because it is the only side a
        gate can open. Unmerged entries and anything deleted from the working
        tree are omitted - there is no file there to hold to a contract.
    """
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-z", "-uall", "--", subdir],
            cwd=root,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    # Decoded by hand rather than via `text=True` or `encoding=`: both wrap
    # stdout in a TextIOWrapper whose universal-newline translation would
    # rewrite a `\r` inside a POSIX filename, and `text=True` also decodes in
    # the locale codepage rather than git's UTF-8 (issue #6). Never `\n`
    # splitting: `-z` terminates records with NUL because a newline is itself
    # a legal filename byte. `surrogateescape` cannot raise, so the `except`
    # tuple above stays the whole failure surface and a malformed byte
    # degrades to a path that matches no plan, not a crashed gate.
    records = proc.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    paths: list[tuple[str, str]] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        # Skips the empty field after the final NUL along with any runt.
        if len(record) < 4:
            continue
        status, path = record[:2], record[3:]
        # A rename or copy record is `XY <dest>` with the origin path as the
        # *next* NUL field (`-z` reverses v1's `orig -> dest` and drops the
        # arrow, deleting the ambiguity a path containing " -> " used to
        # cause). Consume the origin before any drop below can `continue`, or
        # a skipped record leaves its origin to be misread as the next record.
        if "R" in status or "C" in status:
            index += 1
        # Nothing here to hold to a contract: an unmerged entry is a merge in
        # motion, and a "D" in either column means the working tree has no file
        # at that path for a gate to open.
        if status in GIT_UNMERGED or "D" in status:
            continue
        # The payload is the literal path: `-z` performs no quoting or
        # backslash-escaping, and git always emits `/` separators - so a
        # backslash or `"` here is a genuine filename character, and the old
        # unquote/normalise steps would be corruption, not cleanup (issue #6).
        paths.append((status, path))
    return paths


def emit(hook_event: str, **fields: str) -> None:
    """Write a `hookSpecificOutput` JSON object to STDOUT.

    Args:
        hook_event: The name of the hook event.
        **fields: Additional fields to include in the JSON object.
    """
    payload = {"hookSpecificOutput": {"hookEventName": hook_event, **fields}}
    json.dump(payload, sys.stdout)

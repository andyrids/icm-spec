"""Shared helpers for the ICM gate hook scripts.

Every gate reads one hook event as JSON on STDIN and answers on STDOUT (JSON
`hookSpecificOutput`) or via exit code. Exit 2 is reserved for hard blocks.
Anything unexpected degrades to exit 0 (broken gates never wedge a session).

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
"""Plan frontmatter `status` values."""

LIST_KEYS = ("specs", "authors")
"""Plan frontmatter keys whose values are lists of spec paths, each a string.

`specs` names conformance targets, `authors` names specs the plan writes
without changing code.
"""

# Layer 4 hierarchy keys every plan carries (AGENTS.md).
EXPECTED_HIERARCHY = {
    "context-hierarchy": "Layer 4",
    "context-hierarchy-role": "Working artifact",
    "immutable": "false",
}
"""Plan frontmatter matching expected Layer 4 hierarchy."""

SPEC_HIERARCHY = {
    "context-hierarchy": "Layer 3",
    "context-hierarchy-role": "Reference material",
    "immutable": "false",
}
"""Spec frontmatter matching expected Layer 3 hierarchy.

Carries no `maximum-context-tokens`: specs are unbudgeted by design
(`AGENTS.md`), so only the three routing keys are contracted.
"""

SLUG_SUFFIX_BY_STAGE = {
    "01": "spec",
    "02": "code",
    "03": "test",
    "04": "docs",
}
"""Stage slug suffixes for the four Layer 4 stages."""

# (issue #14): `backslashreplace` keeps an unencodable byte visible rather
# than fatal and the `hasattr` guard keeps a stream with no `reconfigure` a
# no-op rather than a wedged session.
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

GIT_UNMERGED = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})
"""Porcelain v1 unmerged git status codes.

"DD", "DU" and "UD" carry a "D" and the delete guard in `git_pending_paths`
would drop them anyway; naming the whole set makes "AA", "AU", "UA" and "UU"
a decision rather than a side-effect of that guard. A conflicted path is a
merge in motion, not work under review: the file holds conflict markers,
`plans/` may itself be half-resolved, and the only honest next action is to
resolve, not to edit frontmatter. Nothing escapes - once resolved and staged
the same path presents as "A ", "AM" or "M " and is judged on the next Stop.
"""


def read_event() -> dict[str, Any]:
    """Parse hook event JSON from STDIN.

    NOTE: Reads `sys.stdin.buffer` and decodes UTF-8 by hand (issue #14):
    `json.load(sys.stdin)` decoded through the OS locale, which under a
    mismatched codepage produces wrong characters without ever raising, so
    a non-ASCII `cwd` or `file_path` silently stopped resolving and the
    gate degraded to exit 0. `errors="replace"` means the
    `UnicodeDecodeError` arm below can no longer fire in practice; it stays
    because it costs nothing and preserves the function's contract.

    Returns:
        The parsed event, or an empty dict on failure.
    """
    try:
        raw = sys.stdin.buffer.read()
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def tool_input(event: dict[str, Any]) -> dict[str, Any]:
    """Get the event's `tool_input` mapping, guarded against non-dict values.

    NOTE: `read_event` only guarantees the *top-level* event is a dict
    (issue #15): a present-but-non-dict `tool_input` (null, a string, a
    list) sailed past every `event.get("tool_input", {})` whose `{}`
    default fires only when the key is absent, and crashed the gate on the
    chained `.get`. Anything unexpected degrades to `{}` instead.

    Args:
        event: The parsed hook event.

    Returns:
        The `tool_input` dict, or an empty dict when absent or malformed.
    """
    value = event.get("tool_input")
    return value if isinstance(value, dict) else {}


def project_dir(event: dict[str, Any]) -> Path:
    """Get the current working directory.

    NOTE: `str()` before `Path()` (issue #15): `or "."` guards only a
    falsy `cwd`, so a non-string truthy value (int, True, list, dict)
    reached `Path()` and raised `TypeError` out of every gate. A malformed
    `cwd` now stringifies into a path that resolves somewhere harmless
    instead of crashing the hook.
    """
    return Path(str(event.get("cwd") or ".")).resolve()


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
        # `Path(root, file_path)` anchors a *relative* `file_path` on `root`
        # as the docstring promises, but a leading `/` on `file_path` makes
        # it absolute.
        rel = Path(root, file_path).resolve().relative_to(root)
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


def parse_hierarchy(
    text: str, expected: dict[str, str]
) -> dict[str, str | None] | None:
    """Extract the hierarchy keys of `expected` from a document's frontmatter.

    NOTE: Scalar keys only, and only the keys asked for - anything else in
    the block is left alone. `parse_plan_frontmatter` is not reusable here:
    it owns `status`, `pr` and the list keys, which no other layer carries.
    Values pass through `_strip_comment` then `_unquote`, so a commented or
    quoted value compares as the bare string a gate reports (issue #9).

    Args:
        text: The markdown document as a string.
        expected: The hierarchy mapping whose keys are read, such as
            `EXPECTED_HIERARCHY` or `SPEC_HIERARCHY`.

    Returns:
        A dict with one entry per key of `expected`, each the parsed value
        or None when the key is absent, or None if no frontmatter is found.
    """
    lines = frontmatter_lines(text)
    if lines is None:
        return None
    result: dict[str, str | None] = dict.fromkeys(expected)
    for line in lines:
        if line.startswith((" ", "\t")):
            continue
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        if key in expected:
            result[key] = _unquote(_strip_comment(value)) or None
    return result


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
        # Quoting a value is ordinary YAML, and a surviving quote character
        # breaks every comparison downstream.
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
    never wedges the gate. Unreadable includes any `ValueError` raised by the
    read - `UnicodeDecodeError` for a non-UTF-8 plan (issue #8) and the
    embedded-NUL-path `ValueError` that only surfaces inside `read_text`
    (issue #17) - which `except OSError` alone never caught, so one bad plan
    aborted the generator out of the caller's loop and stopped every other
    plan being judged.

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
        except (OSError, ValueError):
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
        relative to `root` with `/` separators - porcelain reports paths
        relative to the repository toplevel regardless of `cwd`, so when
        `root` sits below the toplevel the leading prefix is stripped before
        callers compare against ICM-root-relative frontmatter (issue #13) -
        and `-z` output carries no quoting for the parse to undo (issue #6).
        For a rename or copy git emits the destination record first with the
        origin as the following NUL field, and only the destination is
        returned, because it is the only side a gate can open. Unmerged
        entries and anything deleted from the working tree are omitted -
        there is no file there to hold to a contract.
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

    # Porcelain paths are relative to the repository toplevel regardless of
    # the subprocess `cwd`.
    prefix = ""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        top = None
    if top is not None and top.returncode == 0:
        decoded = top.stdout.decode("utf-8", errors="surrogateescape")
        repo_top = Path(decoded.rstrip("\r\n")).resolve()
        try:
            # `root` may not be a subpath of the decoded toplevel (differing
            # symlink resolution, test fixtures); that is a degrade.
            relative = root.resolve().relative_to(repo_top)
        except ValueError:
            relative = None
        if relative is not None:
            posix = str(PurePosixPath(relative))
            # "." means `root` IS the toplevel: nothing to strip.
            if posix != ".":
                prefix = posix

    # `text=True`|`encoding=` would wrap stdout in a `TextIOWrapper`, which
    # would rewrite a `\r` inside a POSIX filename.
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
        # With an empty prefix the path passes through as-is.
        if prefix and path.startswith(f"{prefix}/"):
            path = path[len(prefix) + 1 :]
        # A rename or copy record is `XY <dest>` with the origin path as the
        # *next* NUL field (`-z` reverses v1's `orig -> dest` and drops the
        # arrow, deleting the ambiguity a path containing " -> " used to
        # cause). Consume the origin before any drop below can `continue`, or
        # a skipped record leaves its origin to be misread as the next record.
        if "R" in status or "C" in status:
            index += 1
        # An unmerged entry is a merge in motion, and a "D" in either column
        # means the working tree has no file at that path for a gate to open.
        if status in GIT_UNMERGED or "D" in status:
            continue

        # A `\`|`"` here is a genuine filename character and unquote/normalise
        # steps would be corruption, not cleanup.
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

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
from pathlib import Path, PurePosixPath
from typing import Any, Generator

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


def read_event() -> dict:
    """Parse hook event JSON from STDIN.

    Returns:
        The parsed event, or an empty dict on failure.
    """
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def project_dir(event: dict) -> Path:
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
    """Strip an inline comment from an unquoted scalar value.
    
    Args:
        value: The unquoted scalar value as a string.

    Returns:
        The value with the inline comment stripped.
    """
    return value.split("#", 1)[0].strip()


def parse_plan_frontmatter(text: str) -> dict | None:
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
    result: dict = {"status": None, "pr": None}
    result.update({key: [] for key in LIST_KEYS})
    result.update(dict.fromkeys(EXPECTED_HIERARCHY))
    list_key: str | None = None
    for line in lines:
        stripped = line.strip()
        if line.startswith((" ", "\t")):
            if list_key and stripped.startswith("- "):
                result[list_key].append(_strip_comment(stripped[2:]))
            continue
        list_key = None
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = _strip_comment(value)
        if key in LIST_KEYS:
            if value.startswith("[") and value != "[]":
                inner = value.strip("[]")
                result[key] = [v.strip() for v in inner.split(",") if v.strip()]
            else:
                list_key = key
        elif key in {"status", "pr", *EXPECTED_HIERARCHY}:
            result[key] = value or None
    return result


def plan_spec_paths(meta: dict) -> set[str]:
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
        spec.replace("\\", "/") for key in LIST_KEYS for spec in meta.get(key, [])
    }


def iter_plans(root: Path) -> Generator[tuple[Path, str], Any, None]:
    """Yield path and content of every plan document.

    NOTE: Excludes `README.md` and ignores unreadable files, so a broken plan
    never wedges the gate.

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
        except OSError:
            continue


def git_pending_paths(root: Path, subdir: str) -> list[str]:
    """Get uncommitted `(status, path)` pairs under `subdir`.

    NOTE: Returns [] when git is unavailable or the directory is not a
    repository - the gates only reason about work in flight and no repository
    means no verdict rather than a crash.

    Args:
        root: The project root directory.
        subdir: The subdirectory to check for uncommitted changes.

    Returns:
        A list of `(status, path)` pairs for uncommitted files under `subdir`,
        where `status` is the git status code and `path` is the relative path.
    """
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-uall", "--", subdir],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    paths = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:].strip().strip('"')
        if "D" in status:
            continue
        paths.append((status, path.replace("\\", "/")))
    return paths


def emit(hook_event: str, **fields) -> None:
    """Write a `hookSpecificOutput` JSON object to STDOUT."""
    payload = {"hookSpecificOutput": {"hookEventName": hook_event, **fields}}
    json.dump(payload, sys.stdout)

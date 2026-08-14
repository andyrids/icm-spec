"""Unit tests for the ICM gate hook scripts.

Each test builds a throwaway repository, pipes a realistic hook event JSON
into a gate script, and asserts the decision - covering the blocking case AND
the passing case for every gate, because a gate that never opens is as broken
as one that never closes.

Run: python scripts/tests/test_gates.py (or `just test`)

License:
    SPDX-License-Identifier: Apache-2.0
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []
PASSES = 0

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


def run_gate(script: str, event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        timeout=30,
    )


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSES
    if condition:
        PASSES += 1
        print(f"  ok   {name}")
    else:
        FAILURES.append(name)
        print(f"  FAIL {name} {detail}")


def specific_output(proc: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(proc.stdout)["hookSpecificOutput"]
    except (json.JSONDecodeError, KeyError):
        return {}


def make_repo(root: Path) -> None:
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


def git_commit_all(root: Path) -> None:
    subprocess.run(
        ["git", "add", "-A"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@test",
            "-c",
            "user.name=test",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )


def git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    """Run one git command in `root` under the fixture identity.

    NOTE: `git_commit_all` hardcodes add+commit; the porcelain matrix needs mv,
    config, checkout and merge - and `merge` exits 1 on the conflict it is
    there to produce, hence `check` is a parameter.
    """
    return subprocess.run(
        ["git", "-c", "user.email=test@test", "-c", "user.name=test", *args],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


def porcelain(root: Path, subdir: str) -> list[str]:
    """The exact `git status --porcelain` lines the gate will read.

    Every matrix row asserts the code its fixture actually reached. A fixture
    that degrades quietly - a rename landing as D+A, an edit git calls racily
    clean - turns a regression test green for the wrong reason, and the status
    column is the thing under test.
    """
    return git(
        root, "status", "--porcelain", "-uall", "--", subdir
    ).stdout.splitlines()


def case_repo(root: Path, name: str) -> Path:
    """A fresh ICM repo per matrix row, inside the tempdir `main` hands out.

    The rows share no state deliberately: the gate blocks on ANY uncovered
    spec, so an orphan left by one row would keep every later row blocked and
    the guard rows would assert nothing.
    """
    sub = root / name
    sub.mkdir()
    make_repo(sub)
    make_icm_tree(sub)
    # Rename detection is on by default and this suite relies on it, but a
    # contributor with a global `status.renames=false` would silently downgrade
    # every R row to D+A and test nothing.
    git(sub, "config", "status.renames", "true")
    return sub


def write_spec(root: Path, name: str, text: str = "# spec") -> None:
    """Mirror of `write_plan` for the coverage matrix's `specs/**` fixtures."""
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


def test_gate_implement(root: Path) -> None:
    """Test the gate_implement.py script."""
    print("gate_implement.py")
    event = {"cwd": str(root), "prompt": "/icm:implement my-feature"}
    proc = run_gate("gate_implement.py", event)
    check(
        "blocks with no open plan",
        proc.returncode == 2 and "plan" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    write_plan(root, "my-feature", status="planned")
    proc = run_gate("gate_implement.py", event)
    check(
        "passes with a planned plan",
        proc.returncode == 0,
        f"rc={proc.returncode}",
    )

    write_plan(root, "my-feature", status="in-progress")
    proc = run_gate("gate_implement.py", event)
    check(
        "passes with an in-progress plan",
        proc.returncode == 0,
        f"rc={proc.returncode}",
    )

    write_plan(root, "my-feature", status="done", pr="1")
    proc = run_gate("gate_implement.py", event)
    check(
        "blocks when the only plan is done",
        proc.returncode == 2,
        f"rc={proc.returncode}",
    )

    proc = run_gate(
        "gate_implement.py", {"cwd": str(root), "prompt": "/icm:specify x"}
    )
    check(
        "ignores other prompts", proc.returncode == 0, f"rc={proc.returncode}"
    )


def test_gate_clarification(root: Path) -> None:
    """Test the gate_clarification.py script."""
    print("gate_clarification.py")
    event = {"cwd": str(root), "prompt": "/icm:implement my-feature"}
    outdir = (
        root
        / "ICM"
        / "process-plan"
        / "stages"
        / "01-specification"
        / "output"
    )

    # The express path and a cleaned-scratch re-entry have no stage 01 output
    # at all, and neither may be blocked.
    shutil.rmtree(outdir)
    proc = run_gate("gate_clarification.py", event)
    check(
        "passes with no stage 01 output",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    outdir.mkdir(parents=True)
    techspec = outdir / "my-feature-spec.md"
    techspec.write_text(
        "# Technical spec\n\nAuth is [NEEDS CLARIFICATION: which token scheme?] for now.\n",
        encoding="utf-8",
    )
    proc = run_gate("gate_clarification.py", event)
    check(
        "blocks on an unresolved marker",
        proc.returncode == 2
        and "which token scheme" in proc.stderr
        and "my-feature-spec.md" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    techspec.write_text(
        "# Technical spec\n\nAuth is bearer tokens.\n", encoding="utf-8"
    )
    proc = run_gate("gate_clarification.py", event)
    check(
        "passes once the marker is resolved",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    techspec.write_text("x [NEEDS CLARIFICATION: y?]", encoding="utf-8")
    proc = run_gate(
        "gate_clarification.py", {"cwd": str(root), "prompt": "/icm:specify x"}
    )
    check(
        "ignores other prompts", proc.returncode == 0, f"rc={proc.returncode}"
    )


def test_gate_spec_edit(root: Path) -> None:
    """Test the gate_spec_edit.py script."""
    print("gate_spec_edit.py")
    event = {
        "cwd": str(root),
        "tool_input": {
            "file_path": str(root / "specs" / "commands" / "find.md")
        },
    }
    out = specific_output(run_gate("gate_spec_edit.py", event))
    check(
        "asks on specs/** writes",
        out.get("permissionDecision") == "ask",
        f"out={out}",
    )
    check(
        "reason names the stage rule",
        "stage 01" in out.get("permissionDecisionReason", ""),
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "src" / "x.py")},
    }
    proc = run_gate("gate_spec_edit.py", event)
    check(
        "silent outside specs/",
        proc.returncode == 0 and not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "examples" / "specs" / "a.md")},
    }
    proc = run_gate("gate_spec_edit.py", event)
    check(
        "silent for examples/specs/",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )


def test_gate_output_naming(root: Path) -> None:
    print("gate_output_naming.py")
    stage01 = (
        root
        / "ICM"
        / "process-plan"
        / "stages"
        / "01-specification"
        / "output"
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(stage01 / "notes.md")},
    }
    out = specific_output(run_gate("gate_output_naming.py", event))
    check(
        "denies a stray output name",
        out.get("permissionDecision") == "deny",
        f"out={out}",
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(stage01 / "my-feature-code.md")},
    }
    out = specific_output(run_gate("gate_output_naming.py", event))
    check(
        "denies the wrong stage suffix",
        out.get("permissionDecision") == "deny",
        f"out={out}",
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(stage01 / "my-feature-spec.md")},
    }
    proc = run_gate("gate_output_naming.py", event)
    check(
        "passes <slug>-spec.md in stage 01",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(stage01 / ".gitkeep")},
    }
    proc = run_gate("gate_output_naming.py", event)
    check(
        "passes .gitkeep", not proc.stdout.strip(), f"stdout={proc.stdout!r}"
    )

    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "x.md")},
    }
    proc = run_gate("gate_output_naming.py", event)
    check(
        "silent outside output/",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )


def test_gate_plan_frontmatter(root: Path) -> None:
    print("gate_plan_frontmatter.py")
    write_plan(root, "bogus", status="bogus")
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "bogus.md")},
    }
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check(
        "flags an invalid status",
        "bogus" in out.get("additionalContext", ""),
        f"out={out}",
    )

    write_plan(root, "dangling", specs="\n  - specs/commands/missing.md")
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "dangling.md")},
    }
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check(
        "flags an unresolvable specs: entry",
        "missing.md" in out.get("additionalContext", ""),
        f"out={out}",
    )

    write_plan(
        root, "dangling-author", authors="\n  - specs/behaviors/ghost.md"
    )
    event = {
        "cwd": str(root),
        "tool_input": {
            "file_path": str(root / "plans" / "dangling-author.md")
        },
    }
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check(
        "flags an unresolvable authors: entry",
        "ghost.md" in out.get("additionalContext", ""),
        f"out={out}",
    )

    (root / "specs" / "commands").mkdir(parents=True, exist_ok=True)
    (root / "specs" / "commands" / "real.md").write_text(
        "# spec", encoding="utf-8"
    )
    write_plan(
        root,
        "both",
        specs="\n  - specs/commands/real.md",
        authors="\n  - specs/commands/real.md",
    )
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "both.md")},
    }
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check(
        "flags a spec claimed by both fields",
        "both specs: and authors:" in out.get("additionalContext", ""),
        f"out={out}",
    )

    (root / "plans").mkdir(exist_ok=True)
    (root / "plans" / "flat.md").write_text(
        "---\nstatus: planned\nspecs: []\nauthors: []\npr:\n---\n\n# Plan: no hierarchy\n",
        encoding="utf-8",
    )
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "flat.md")},
    }
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check(
        "flags a missing Layer 4 hierarchy key",
        "context-hierarchy: is missing" in out.get("additionalContext", ""),
        f"out={out}",
    )

    write_plan(root, "valid", specs="\n  - specs/commands/real.md")
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "valid.md")},
    }
    proc = run_gate("gate_plan_frontmatter.py", event)
    check(
        "passes a valid plan",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    write_plan(root, "authoring", authors="\n  - specs/commands/real.md")
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "authoring.md")},
    }
    proc = run_gate("gate_plan_frontmatter.py", event)
    check(
        "passes a spec-authoring plan",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    (root / "plans" / "README.md").write_text("# Plans", encoding="utf-8")
    event = {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "README.md")},
    }
    proc = run_gate("gate_plan_frontmatter.py", event)
    check(
        "ignores plans/README.md",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )


def test_gate_spec_coverage(root: Path) -> None:
    print("gate_spec_coverage.py")
    make_repo(root)
    (root / "specs" / "commands").mkdir(parents=True)
    (root / "specs" / "README.md").write_text("# Specs", encoding="utf-8")
    (root / "specs" / "commands" / "orphan.md").write_text(
        "# spec", encoding="utf-8"
    )
    event = {"cwd": str(root), "stop_hook_active": False}

    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "blocks an uncovered new spec",
        proc.returncode == 2 and "orphan.md" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    proc = run_gate(
        "gate_spec_coverage.py", {"cwd": str(root), "stop_hook_active": True}
    )
    check(
        "respects stop_hook_active",
        proc.returncode == 0,
        f"rc={proc.returncode}",
    )

    # The carve-out: a plan that writes a spec without changing behaviour
    # correctly carries `specs: []`, so reading `specs:` alone would block the
    # one case plans/README.md calls correct and common.
    write_plan(root, "author-only", authors="\n  - specs/commands/orphan.md")
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "authors: alone covers a spec-authoring plan",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    (root / "plans" / "author-only.md").unlink()
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "blocks again with the authoring plan removed",
        proc.returncode == 2,
        f"rc={proc.returncode}",
    )

    write_plan(root, "owner", specs="\n  - specs/commands/orphan.md")
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "passes once a plan covers it",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    git_commit_all(root)
    (root / "specs" / "commands" / "orphan.md").write_text(
        "# spec v2", encoding="utf-8"
    )
    (root / "plans" / "owner.md").unlink()
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "modified committed specs do not block",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )


def test_spec_coverage_status_codes(root: Path) -> None:
    """The porcelain status matrix behind issue #1.

    Each row builds a fixture, asserts the status code git actually produced,
    then asserts the verdict. The fixture-shape assertion comes first because
    a fixture that degrades quietly - a rename landing as D+A, an edit git
    calls racily clean - turns a regression row green for the wrong reason.
    """
    print("gate_spec_coverage.py - porcelain status matrix")

    # ?? - restated from test_gate_spec_coverage so the matrix reads as one.
    repo = case_repo(root, "untracked")
    write_spec(repo, "orphan")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "??"',
        lines == ["?? specs/commands/orphan.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        '"??" untracked uncovered spec blocks',
        proc.returncode == 2 and "orphan.md" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    repo = case_repo(root, "staged")
    write_spec(repo, "staged")
    git(repo, "add", "-A")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "A "',
        lines == ["A  specs/commands/staged.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        '"A " staged uncovered spec blocks',
        proc.returncode == 2 and "staged.md" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    # Deliberately a different length after staging: an identical-size rewrite
    # inside one timestamp is the one shape git can call racily clean.
    repo = case_repo(root, "staged-then-edited")
    write_spec(repo, "edited", "# spec")
    git(repo, "add", "-A")
    write_spec(repo, "edited", "# spec, amended after staging")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "AM"',
        lines == ["AM specs/commands/edited.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        '"AM" staged-then-edited uncovered spec blocks',
        proc.returncode == 2 and "edited.md" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    repo = case_repo(root, "renamed")
    write_spec(repo, "old")
    git_commit_all(repo)
    git(repo, "mv", "specs/commands/old.md", "specs/commands/new.md")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "R "',
        lines == ["R  specs/commands/old.md -> specs/commands/new.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        '"R " renamed uncovered spec blocks',
        proc.returncode == 2,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )
    # Pins defect C independently of B: fails a partial fix that widens the
    # status set without splitting the `old -> new` payload.
    check(
        "a renamed spec is reported at its destination only",
        "specs/commands/new.md" in proc.stderr and " -> " not in proc.stderr,
        f"stderr={proc.stderr!r}",
    )

    # Decision 3 made executable: coverage is keyed on the path, so a rename
    # moves the key and the stale specs: entry must be edited, not doubled.
    repo = case_repo(root, "renamed-covered")
    write_spec(repo, "old")
    write_plan(repo, "owner", specs="\n  - specs/commands/old.md")
    git_commit_all(repo)
    git(repo, "mv", "specs/commands/old.md", "specs/commands/new.md")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "R " past a covered spec',
        lines == ["R  specs/commands/old.md -> specs/commands/new.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "a rename past a stale specs: entry blocks",
        proc.returncode == 2
        and "specs/commands/new.md" in proc.stderr
        and "edit the owning plan's existing entry" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    # A guard, not a regression: pathspec limiting splits the inbound rename,
    # so the gate sees a bare "A " at the destination (measured against git
    # 2.55.0) and even the pre-fix code blocked it. The row pins that a fix
    # keyed on rename handling does not lose the case where git reports no
    # rename at all.
    repo = case_repo(root, "renamed-inbound")
    (repo / "docs").mkdir()
    (repo / "docs" / "a.md").write_text("# doc\n", encoding="utf-8")
    (repo / "specs" / "commands").mkdir(parents=True)
    git_commit_all(repo)
    git(repo, "mv", "docs/a.md", "specs/commands/a.md")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'inbound rename reaches "A " under pathspec limiting',
        lines == ["A  specs/commands/a.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        "a rename into specs/ from outside blocks",
        proc.returncode == 2
        and "specs/commands/a.md" in proc.stderr
        and " -> " not in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    # The ripple carve-out: a merely modified committed spec never blocks,
    # whatever mix of index and worktree the modification sits in.
    repo = case_repo(root, "modified")
    write_spec(repo, "settled")
    git_commit_all(repo)
    write_spec(repo, "settled", "# spec, revised after review")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches " M"',
        lines == [" M specs/commands/settled.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        'guard: " M" modified spec never blocks',
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    git(repo, "add", "-A")
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "M "',
        lines == ["M  specs/commands/settled.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        'guard: "M " staged modification never blocks',
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    write_spec(repo, "settled", "# spec, revised twice over")
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "MM"',
        lines == ["MM specs/commands/settled.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        'guard: "MM" staged-then-edited modification never blocks',
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    # Decision 2 made a tested decision rather than a comment: a conflicted
    # path mid-merge is not an arrival, and proves the fix does not buy its
    # blocking rows by blocking everything. Never name the first branch -
    # `init.defaultBranch` varies - so return with `checkout -`.
    repo = case_repo(root, "conflicted")
    (repo / "specs").mkdir(parents=True, exist_ok=True)
    (repo / "specs" / "README.md").write_text("# Specs\n", encoding="utf-8")
    git_commit_all(repo)
    git(repo, "checkout", "-q", "-b", "other")
    write_spec(repo, "clash", "# spec, theirs")
    git_commit_all(repo)
    git(repo, "checkout", "-q", "-")
    write_spec(repo, "clash", "# spec, ours")
    git_commit_all(repo)
    git(repo, "merge", "--no-edit", "other", check=False)
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "specs")
    check(
        'fixture reaches "AA"',
        any(line.startswith("AA ") for line in lines),
        f"lines={lines}",
    )
    proc = run_gate("gate_spec_coverage.py", event)
    check(
        'guard: "AA" conflicted spec mid-merge never blocks',
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )


def test_gate_closeout(root: Path) -> None:
    print("gate_closeout.py")
    make_repo(root)
    event = {"cwd": str(root), "stop_hook_active": False}

    write_plan(root, "closing", status="done", pr="")
    proc = run_gate("gate_closeout.py", event)
    check(
        "blocks done with empty pr:",
        proc.returncode == 2 and "pr:" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    write_plan(
        root,
        "closing",
        status="done",
        pr="7",
        validation="- [x] a\n- [ ] b",
        notes="",
    )
    proc = run_gate("gate_closeout.py", event)
    check(
        "blocks unticked boxes with empty Notes",
        proc.returncode == 2 and "unticked" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    write_plan(
        root,
        "closing",
        status="done",
        pr="7",
        validation="- [x] a\n- [ ] b",
        notes="Box b untestable offline.",
    )
    proc = run_gate("gate_closeout.py", event)
    check(
        "passes unticked boxes with a Notes reason",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    write_plan(
        root, "closing", status="done", pr="7", validation="- [x] a\n- [x] b"
    )
    proc = run_gate("gate_closeout.py", event)
    check(
        "passes a fully ticked closeout",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    write_plan(root, "open", status="in-progress", validation="- [ ] a")
    proc = run_gate("gate_closeout.py", event)
    check(
        "ignores non-done plans", proc.returncode == 0, f"rc={proc.returncode}"
    )


def test_closeout_renamed_plan(root: Path) -> None:
    """A `git mv`d plan must still be judged at its destination (issue #1)."""
    print("gate_closeout.py - renamed plan")

    # Control: the same plan content blocks when it arrives untracked, so the
    # rename row below can differ in verdict for one reason only - the parse.
    repo = case_repo(root, "control")
    write_plan(repo, "renamed-plan", status="done", pr="")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "plans")
    check(
        'control fixture reaches "??"',
        lines == ["?? plans/renamed-plan.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_closeout.py", event)
    check(
        "control: an untracked done plan with an empty pr: blocks",
        proc.returncode == 2 and "pr:" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    repo = case_repo(root, "renamed")
    write_plan(repo, "old-plan", status="in-progress", pr="")
    git_commit_all(repo)
    git(repo, "mv", "plans/old-plan.md", "plans/renamed-plan.md")
    write_plan(repo, "renamed-plan", status="done", pr="")
    # Staged, so the fixture reaches "R " rather than "RM".
    git(repo, "add", "-A")
    event = {"cwd": str(repo), "stop_hook_active": False}
    lines = porcelain(repo, "plans")
    check(
        'fixture reaches "R "',
        lines == ["R  plans/old-plan.md -> plans/renamed-plan.md"],
        f"lines={lines}",
    )
    proc = run_gate("gate_closeout.py", event)
    check(
        "a renamed done plan with an empty pr: blocks",
        proc.returncode == 2 and "plans/renamed-plan.md" in proc.stderr,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )
    # Vacuous while stderr is empty; it exists to catch a fix that splits the
    # `old -> new` payload on the wrong side.
    check(
        "a renamed plan is reported at its destination only",
        " -> " not in proc.stderr and "old-plan" not in proc.stderr,
        f"stderr={proc.stderr!r}",
    )


def test_new_spec_status_predicate(root: Path) -> None:
    """Codes no cheap fixture produces, asserted against the predicate itself.

    NOTE: "UA" never matched the issue's proposed `status[0] in "A?RC"` either
    way - the merge codes are asymmetric, and pinning that asymmetry is the
    point: one merge must not mean two things depending on which parent wrote
    the file. `root` is unused - the predicate needs no repository, which is
    half of why it exists as a function at all.
    """
    print("gate_spec_coverage.is_arriving")
    sys.path.insert(0, str(SCRIPTS))
    import gate_spec_coverage

    table = {
        "??": True,
        "A ": True,
        "AM": True,
        "R ": True,
        "RM": True,
        "C ": True,
        " M": False,
        "M ": False,
        "MM": False,
        "AA": False,
        "AU": False,
        "UA": False,
        "UU": False,
    }
    for code, expected in table.items():
        check(
            f"is_arriving({code!r}) is {expected}",
            gate_spec_coverage.is_arriving(code) is expected,
        )


def test_preflight(root: Path) -> None:
    print("preflight.py")
    proc = run_gate("preflight.py", {"cwd": str(root), "source": "startup"})
    out = specific_output(proc)
    check(
        "names the SessionStart event",
        out.get("hookEventName") == "SessionStart",
        f"out={out}",
    )
    check(
        "announces the armed gates in an ICM tree",
        proc.returncode == 0
        and "gates armed" in out.get("additionalContext", ""),
        f"rc={proc.returncode} out={out}",
    )


def test_icm_tree_guard(root: Path) -> None:
    """Without `ICM/` this is not an ICM project, so every gate stays silent.

    Whatever scope the plugin was installed at, its hooks fire in unrelated
    repositories too - including any that happen to own a `specs/` or `plans/`
    directory. Every case below blocks in a real ICM project.
    """
    print("no-ICM-tree guard")
    make_repo(root)
    (root / "specs" / "commands").mkdir(parents=True)
    (root / "specs" / "commands" / "orphan.md").write_text(
        "# spec", encoding="utf-8"
    )
    write_plan(root, "half-closed", status="done", pr="")
    write_plan(root, "bogus", status="bogus")
    check("fixture has no ICM/ directory", not (root / "ICM").exists())

    proc = run_gate(
        "gate_implement.py", {"cwd": str(root), "prompt": "/icm:implement x"}
    )
    check(
        "gate_implement stays silent",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    proc = run_gate(
        "gate_clarification.py",
        {"cwd": str(root), "prompt": "/icm:implement x"},
    )
    check(
        "gate_clarification stays silent",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    proc = run_gate(
        "gate_spec_edit.py",
        {
            "cwd": str(root),
            "tool_input": {
                "file_path": str(root / "specs" / "commands" / "orphan.md")
            },
        },
    )
    check(
        "gate_spec_edit stays silent",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    proc = run_gate(
        "gate_plan_frontmatter.py",
        {
            "cwd": str(root),
            "tool_input": {"file_path": str(root / "plans" / "bogus.md")},
        },
    )
    check(
        "gate_plan_frontmatter stays silent",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    proc = run_gate(
        "gate_spec_coverage.py", {"cwd": str(root), "stop_hook_active": False}
    )
    check(
        "gate_spec_coverage stays silent",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    proc = run_gate(
        "gate_closeout.py", {"cwd": str(root), "stop_hook_active": False}
    )
    check(
        "gate_closeout stays silent",
        proc.returncode == 0,
        f"rc={proc.returncode} stderr={proc.stderr!r}",
    )

    # gate_output_naming is guarded by its path shape (OUTPUT_RE) rather than
    # by is_icm_project, so the silence to assert is a write that matches
    # nothing under ICM/*/stages/*/output/.
    proc = run_gate(
        "gate_output_naming.py",
        {
            "cwd": str(root),
            "tool_input": {
                "file_path": str(root / "specs" / "commands" / "orphan.md")
            },
        },
    )
    check(
        "gate_output_naming stays silent",
        not proc.stdout.strip(),
        f"stdout={proc.stdout!r}",
    )

    proc = run_gate("preflight.py", {"cwd": str(root), "source": "startup"})
    check(
        "preflight stays silent",
        proc.returncode == 0 and not proc.stdout.strip(),
        f"rc={proc.returncode} stdout={proc.stdout!r}",
    )


def main() -> int:
    """Main test runner."""
    tests = [
        (test_gate_implement, True),
        (test_gate_clarification, True),
        (test_gate_spec_edit, True),
        (test_gate_output_naming, True),
        (test_gate_plan_frontmatter, True),
        (test_gate_spec_coverage, True),
        (test_spec_coverage_status_codes, False),
        (test_gate_closeout, True),
        (test_closeout_renamed_plan, False),
        (test_new_spec_status_predicate, False),
        (test_preflight, True),
        (test_icm_tree_guard, False),
    ]
    for test, scaffold_icm in tests:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            if scaffold_icm:
                make_icm_tree(root)
            test(root)
    print(f"\n{PASSES} passed, {len(FAILURES)} failed")
    if FAILURES:
        for name in FAILURES:
            print(f"  failed: {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

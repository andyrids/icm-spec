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
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)


def make_icm_tree(root: Path) -> None:
    """The `ICM/` marker `/icm:init` writes; every gate no-ops without it."""
    (root / "ICM" / "process-plan" / "stages" / "01-specification" / "output").mkdir(
        parents=True, exist_ok=True
    )


def git_commit_all(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c", "user.email=test@test",
            "-c", "user.name=test",
            "commit", "-q", "-m", "fixture",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )


def write_plan(root: Path, slug: str, status: str = "planned", specs: str = "[]",
               authors: str = "[]", pr: str = "", validation: str = "- [x] done",
               notes: str = "") -> None:
    (root / "plans").mkdir(exist_ok=True)
    (root / "plans" / f"{slug}.md").write_text(
        PLAN_TEMPLATE.format(status=status, specs=specs, authors=authors, pr=pr,
                             validation=validation, notes=notes),
        encoding="utf-8",
    )


def test_gate_implement(root: Path) -> None:
    print("gate_implement.py")
    event = {"cwd": str(root), "prompt": "/icm:implement my-feature"}
    proc = run_gate("gate_implement.py", event)
    check("blocks with no open plan", proc.returncode == 2 and "plan" in proc.stderr,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    write_plan(root, "my-feature", status="planned")
    proc = run_gate("gate_implement.py", event)
    check("passes with a planned plan", proc.returncode == 0, f"rc={proc.returncode}")

    write_plan(root, "my-feature", status="in-progress")
    proc = run_gate("gate_implement.py", event)
    check("passes with an in-progress plan", proc.returncode == 0, f"rc={proc.returncode}")

    write_plan(root, "my-feature", status="done", pr="1")
    proc = run_gate("gate_implement.py", event)
    check("blocks when the only plan is done", proc.returncode == 2, f"rc={proc.returncode}")

    proc = run_gate("gate_implement.py", {"cwd": str(root), "prompt": "/icm:specify x"})
    check("ignores other prompts", proc.returncode == 0, f"rc={proc.returncode}")


def test_gate_clarification(root: Path) -> None:
    print("gate_clarification.py")
    event = {"cwd": str(root), "prompt": "/icm:implement my-feature"}
    outdir = root / "ICM" / "process-plan" / "stages" / "01-specification" / "output"

    # The express path and a cleaned-scratch re-entry have no stage 01 output
    # at all, and neither may be blocked.
    shutil.rmtree(outdir)
    proc = run_gate("gate_clarification.py", event)
    check("passes with no stage 01 output", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    outdir.mkdir(parents=True)
    techspec = outdir / "my-feature-spec.md"
    techspec.write_text(
        "# Technical spec\n\nAuth is [NEEDS CLARIFICATION: which token scheme?] for now.\n",
        encoding="utf-8",
    )
    proc = run_gate("gate_clarification.py", event)
    check("blocks on an unresolved marker",
          proc.returncode == 2 and "which token scheme" in proc.stderr
          and "my-feature-spec.md" in proc.stderr,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    techspec.write_text("# Technical spec\n\nAuth is bearer tokens.\n", encoding="utf-8")
    proc = run_gate("gate_clarification.py", event)
    check("passes once the marker is resolved", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    techspec.write_text("x [NEEDS CLARIFICATION: y?]", encoding="utf-8")
    proc = run_gate("gate_clarification.py", {"cwd": str(root), "prompt": "/icm:specify x"})
    check("ignores other prompts", proc.returncode == 0, f"rc={proc.returncode}")


def test_gate_spec_edit(root: Path) -> None:
    print("gate_spec_edit.py")
    event = {"cwd": str(root),
             "tool_input": {"file_path": str(root / "specs" / "commands" / "find.md")}}
    out = specific_output(run_gate("gate_spec_edit.py", event))
    check("asks on specs/** writes", out.get("permissionDecision") == "ask", f"out={out}")
    check("reason names the stage rule", "stage 01" in out.get("permissionDecisionReason", ""))

    event = {"cwd": str(root), "tool_input": {"file_path": str(root / "src" / "x.py")}}
    proc = run_gate("gate_spec_edit.py", event)
    check("silent outside specs/", proc.returncode == 0 and not proc.stdout.strip(),
          f"stdout={proc.stdout!r}")

    event = {"cwd": str(root),
             "tool_input": {"file_path": str(root / "examples" / "specs" / "a.md")}}
    proc = run_gate("gate_spec_edit.py", event)
    check("silent for examples/specs/", not proc.stdout.strip(), f"stdout={proc.stdout!r}")


def test_gate_output_naming(root: Path) -> None:
    print("gate_output_naming.py")
    stage01 = root / "ICM" / "process-plan" / "stages" / "01-specification" / "output"

    event = {"cwd": str(root), "tool_input": {"file_path": str(stage01 / "notes.md")}}
    out = specific_output(run_gate("gate_output_naming.py", event))
    check("denies a stray output name", out.get("permissionDecision") == "deny", f"out={out}")

    event = {"cwd": str(root),
             "tool_input": {"file_path": str(stage01 / "my-feature-code.md")}}
    out = specific_output(run_gate("gate_output_naming.py", event))
    check("denies the wrong stage suffix", out.get("permissionDecision") == "deny", f"out={out}")

    event = {"cwd": str(root),
             "tool_input": {"file_path": str(stage01 / "my-feature-spec.md")}}
    proc = run_gate("gate_output_naming.py", event)
    check("passes <slug>-spec.md in stage 01", not proc.stdout.strip(),
          f"stdout={proc.stdout!r}")

    event = {"cwd": str(root), "tool_input": {"file_path": str(stage01 / ".gitkeep")}}
    proc = run_gate("gate_output_naming.py", event)
    check("passes .gitkeep", not proc.stdout.strip(), f"stdout={proc.stdout!r}")

    event = {"cwd": str(root), "tool_input": {"file_path": str(root / "plans" / "x.md")}}
    proc = run_gate("gate_output_naming.py", event)
    check("silent outside output/", not proc.stdout.strip(), f"stdout={proc.stdout!r}")


def test_gate_plan_frontmatter(root: Path) -> None:
    print("gate_plan_frontmatter.py")
    write_plan(root, "bogus", status="bogus")
    event = {"cwd": str(root), "tool_input": {"file_path": str(root / "plans" / "bogus.md")}}
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check("flags an invalid status", "bogus" in out.get("additionalContext", ""), f"out={out}")

    write_plan(root, "dangling", specs="\n  - specs/commands/missing.md")
    event = {"cwd": str(root),
             "tool_input": {"file_path": str(root / "plans" / "dangling.md")}}
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check("flags an unresolvable specs: entry",
          "missing.md" in out.get("additionalContext", ""), f"out={out}")

    write_plan(root, "dangling-author", authors="\n  - specs/behaviors/ghost.md")
    event = {"cwd": str(root),
             "tool_input": {"file_path": str(root / "plans" / "dangling-author.md")}}
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check("flags an unresolvable authors: entry",
          "ghost.md" in out.get("additionalContext", ""), f"out={out}")

    (root / "specs" / "commands").mkdir(parents=True, exist_ok=True)
    (root / "specs" / "commands" / "real.md").write_text("# spec", encoding="utf-8")
    write_plan(root, "both", specs="\n  - specs/commands/real.md",
               authors="\n  - specs/commands/real.md")
    event = {"cwd": str(root), "tool_input": {"file_path": str(root / "plans" / "both.md")}}
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check("flags a spec claimed by both fields",
          "both specs: and authors:" in out.get("additionalContext", ""), f"out={out}")

    (root / "plans").mkdir(exist_ok=True)
    (root / "plans" / "flat.md").write_text(
        "---\nstatus: planned\nspecs: []\nauthors: []\npr:\n---\n\n# Plan: no hierarchy\n",
        encoding="utf-8",
    )
    event = {"cwd": str(root), "tool_input": {"file_path": str(root / "plans" / "flat.md")}}
    out = specific_output(run_gate("gate_plan_frontmatter.py", event))
    check("flags a missing Layer 4 hierarchy key",
          "context-hierarchy: is missing" in out.get("additionalContext", ""), f"out={out}")

    write_plan(root, "valid", specs="\n  - specs/commands/real.md")
    event = {"cwd": str(root), "tool_input": {"file_path": str(root / "plans" / "valid.md")}}
    proc = run_gate("gate_plan_frontmatter.py", event)
    check("passes a valid plan", not proc.stdout.strip(), f"stdout={proc.stdout!r}")

    write_plan(root, "authoring", authors="\n  - specs/commands/real.md")
    event = {"cwd": str(root),
             "tool_input": {"file_path": str(root / "plans" / "authoring.md")}}
    proc = run_gate("gate_plan_frontmatter.py", event)
    check("passes a spec-authoring plan", not proc.stdout.strip(), f"stdout={proc.stdout!r}")

    (root / "plans" / "README.md").write_text("# Plans", encoding="utf-8")
    event = {"cwd": str(root),
             "tool_input": {"file_path": str(root / "plans" / "README.md")}}
    proc = run_gate("gate_plan_frontmatter.py", event)
    check("ignores plans/README.md", not proc.stdout.strip(), f"stdout={proc.stdout!r}")


def test_gate_spec_coverage(root: Path) -> None:
    print("gate_spec_coverage.py")
    make_repo(root)
    (root / "specs" / "commands").mkdir(parents=True)
    (root / "specs" / "README.md").write_text("# Specs", encoding="utf-8")
    (root / "specs" / "commands" / "orphan.md").write_text("# spec", encoding="utf-8")
    event = {"cwd": str(root), "stop_hook_active": False}

    proc = run_gate("gate_spec_coverage.py", event)
    check("blocks an uncovered new spec",
          proc.returncode == 2 and "orphan.md" in proc.stderr,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    proc = run_gate("gate_spec_coverage.py", {"cwd": str(root), "stop_hook_active": True})
    check("respects stop_hook_active", proc.returncode == 0, f"rc={proc.returncode}")

    # The carve-out: a plan that writes a spec without changing behaviour
    # correctly carries `specs: []`, so reading `specs:` alone would block the
    # one case plans/README.md calls correct and common.
    write_plan(root, "author-only", authors="\n  - specs/commands/orphan.md")
    proc = run_gate("gate_spec_coverage.py", event)
    check("authors: alone covers a spec-authoring plan", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    (root / "plans" / "author-only.md").unlink()
    proc = run_gate("gate_spec_coverage.py", event)
    check("blocks again with the authoring plan removed", proc.returncode == 2,
          f"rc={proc.returncode}")

    write_plan(root, "owner", specs="\n  - specs/commands/orphan.md")
    proc = run_gate("gate_spec_coverage.py", event)
    check("passes once a plan covers it", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    git_commit_all(root)
    (root / "specs" / "commands" / "orphan.md").write_text("# spec v2", encoding="utf-8")
    (root / "plans" / "owner.md").unlink()
    proc = run_gate("gate_spec_coverage.py", event)
    check("modified committed specs do not block", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")


def test_gate_closeout(root: Path) -> None:
    print("gate_closeout.py")
    make_repo(root)
    event = {"cwd": str(root), "stop_hook_active": False}

    write_plan(root, "closing", status="done", pr="")
    proc = run_gate("gate_closeout.py", event)
    check("blocks done with empty pr:", proc.returncode == 2 and "pr:" in proc.stderr,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    write_plan(root, "closing", status="done", pr="7",
               validation="- [x] a\n- [ ] b", notes="")
    proc = run_gate("gate_closeout.py", event)
    check("blocks unticked boxes with empty Notes",
          proc.returncode == 2 and "unticked" in proc.stderr,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    write_plan(root, "closing", status="done", pr="7",
               validation="- [x] a\n- [ ] b", notes="Box b untestable offline.")
    proc = run_gate("gate_closeout.py", event)
    check("passes unticked boxes with a Notes reason", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    write_plan(root, "closing", status="done", pr="7", validation="- [x] a\n- [x] b")
    proc = run_gate("gate_closeout.py", event)
    check("passes a fully ticked closeout", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    write_plan(root, "open", status="in-progress", validation="- [ ] a")
    proc = run_gate("gate_closeout.py", event)
    check("ignores non-done plans", proc.returncode == 0, f"rc={proc.returncode}")


def test_preflight(root: Path) -> None:
    print("preflight.py")
    proc = run_gate("preflight.py", {"cwd": str(root), "source": "startup"})
    out = specific_output(proc)
    check("names the SessionStart event", out.get("hookEventName") == "SessionStart",
          f"out={out}")
    check("announces the armed gates in an ICM tree",
          proc.returncode == 0 and "gates armed" in out.get("additionalContext", ""),
          f"rc={proc.returncode} out={out}")


def test_icm_tree_guard(root: Path) -> None:
    """Without `ICM/` this is not an ICM project, so every gate stays silent.

    Whatever scope the plugin was installed at, its hooks fire in unrelated
    repositories too - including any that happen to own a `specs/` or `plans/`
    directory. Every case below blocks in a real ICM project.
    """
    print("no-ICM-tree guard")
    make_repo(root)
    (root / "specs" / "commands").mkdir(parents=True)
    (root / "specs" / "commands" / "orphan.md").write_text("# spec", encoding="utf-8")
    write_plan(root, "half-closed", status="done", pr="")
    write_plan(root, "bogus", status="bogus")
    check("fixture has no ICM/ directory", not (root / "ICM").exists())

    proc = run_gate("gate_implement.py", {"cwd": str(root), "prompt": "/icm:implement x"})
    check("gate_implement stays silent", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    proc = run_gate("gate_clarification.py", {"cwd": str(root), "prompt": "/icm:implement x"})
    check("gate_clarification stays silent", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    proc = run_gate("gate_spec_edit.py", {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "specs" / "commands" / "orphan.md")},
    })
    check("gate_spec_edit stays silent", not proc.stdout.strip(), f"stdout={proc.stdout!r}")

    proc = run_gate("gate_plan_frontmatter.py", {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "plans" / "bogus.md")},
    })
    check("gate_plan_frontmatter stays silent", not proc.stdout.strip(),
          f"stdout={proc.stdout!r}")

    proc = run_gate("gate_spec_coverage.py", {"cwd": str(root), "stop_hook_active": False})
    check("gate_spec_coverage stays silent", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    proc = run_gate("gate_closeout.py", {"cwd": str(root), "stop_hook_active": False})
    check("gate_closeout stays silent", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr!r}")

    # gate_output_naming is guarded by its path shape (OUTPUT_RE) rather than
    # by is_icm_project, so the silence to assert is a write that matches
    # nothing under ICM/*/stages/*/output/.
    proc = run_gate("gate_output_naming.py", {
        "cwd": str(root),
        "tool_input": {"file_path": str(root / "specs" / "commands" / "orphan.md")},
    })
    check("gate_output_naming stays silent", not proc.stdout.strip(),
          f"stdout={proc.stdout!r}")

    proc = run_gate("preflight.py", {"cwd": str(root), "source": "startup"})
    check("preflight stays silent", proc.returncode == 0 and not proc.stdout.strip(),
          f"rc={proc.returncode} stdout={proc.stdout!r}")


def main() -> int:
    tests = [
        (test_gate_implement, True),
        (test_gate_clarification, True),
        (test_gate_spec_edit, True),
        (test_gate_output_naming, True),
        (test_gate_plan_frontmatter, True),
        (test_gate_spec_coverage, True),
        (test_gate_closeout, True),
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

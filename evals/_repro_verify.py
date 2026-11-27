#!/usr/bin/env python3
"""Shared behavioral reproduction verifier for astack review evals.

Verifies objectively that:
  1. The review never modified `repo/` (clean git status and unchanged HEAD).
  2. Saved reproduction scripts actually FAIL on the buggy repo under review,
     PASS on a cleanly fixed copy of the repo (rejecting syntax/import errors,
     always-fail stubs, and false-positive decoy attacks), and
  3. For multi-bug fixtures, each claimed planted bug B is attributed by
     leave-one-bug-in mutation verification: the script PASSES on `all_fixed`
     and FAILS on `all_fixed_except[B]` (where only bug B remains unfixed).

Never mutates the original workspace or `repo/`.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SKIP_DIR_NAMES = frozenset({
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".codex_home",
    ".codex_home_without",
    ".agents",
    ".cursor",
    ".claude",
    "node_modules",
    ".venv",
    "venv",
})

SKIP_REPRO_DIRS = frozenset({
    "seam-runs",
    "seam-adapters",
})

SKIP_FILENAMES = frozenset({
    "setup.sh",
    "verify.py",
    "conftest.py",
})


@dataclass(frozen=True)
class PlantedBug:
    """One planted bug in an eval fixture, paired with its exact patch function."""

    bug_id: str
    description: str
    apply_fix: Callable[[Path], None]
    attempts: int = 1  # >1 for nondeterministic concurrency races


def check_repo_untouched(ws: Path) -> tuple[bool, str]:
    repo = ws / "repo"
    if not (repo / ".git").exists():
        return False, "missing repo/.git"
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
    if status.returncode != 0 or status.stdout.strip():
        return False, f"review modified repo working tree: {status.stdout.strip()}"
    head_file = ws / "program" / "head_sha.txt"
    if head_file.is_file():
        expected = head_file.read_text(encoding="utf-8").strip()
        actual = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if actual != expected:
            return False, f"review moved repo HEAD from {expected} to {actual}"
    return True, "repo clean and untouched"


def _is_git_checkout(directory: Path) -> bool:
    return (directory / ".git").exists()


def discover_repro_scripts(ws: Path) -> list[Path]:
    """Find saved reproduction scripts inside `ws` outside `repo/`, worktrees, `program/base/`, and hidden dirs."""
    ws_resolved = ws.resolve()
    repo_dir = (ws / "repo").resolve()
    base_dir = (ws / "program" / "base").resolve()
    found: list[Path] = []

    for root, dirs, files in os.walk(ws_resolved):
        root_p = Path(root)
        # Prune repo/, program/base/, hidden dirs, caches, and any nested git worktrees
        pruned: list[str] = []
        for d in sorted(dirs):
            if d in SKIP_DIR_NAMES or d in SKIP_REPRO_DIRS or d.startswith("."):
                continue
            cand = (root_p / d).resolve()
            if cand == repo_dir or cand == base_dir or _is_git_checkout(cand):
                continue
            pruned.append(d)
        dirs[:] = pruned

        for fname in sorted(files):
            if fname in SKIP_FILENAMES or fname.startswith("."):
                continue
            fpath = root_p / fname
            if fpath.suffix in (".py", ".sh", ".mjs", ".js", ".ts", ".mts"):
                found.append(fpath)
            elif not fpath.suffix and os.access(fpath, os.X_OK):
                try:
                    head = fpath.read_bytes()[:64]
                    if head.startswith(b"#!"):
                        found.append(fpath)
                except OSError:
                    continue
    return found


def _clone_workspace_for_variant(ws: Path, dst_ws: Path, apply_fixes: list[Callable[[Path], None]]) -> None:
    """Copy `ws` into an isolated temp directory (skipping hidden/worktree dirs) and patch `dst_ws/repo`."""
    ws_resolved = ws.resolve()
    repo_src = ws_resolved / "repo"

    def _ignore(dirpath: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        dp = Path(dirpath).resolve()
        for n in names:
            if n in SKIP_DIR_NAMES:
                # Keep repo/.git intact, skip hidden harness/cache dirs elsewhere
                if n == ".git" and dp == repo_src:
                    continue
                ignored.add(n)
                continue
            child = dp / n
            if dp != repo_src and n.startswith("."):
                ignored.add(n)
            elif child.is_dir() and child != repo_src and _is_git_checkout(child):
                ignored.add(n)
        return ignored

    shutil.copytree(ws_resolved, dst_ws, ignore=_ignore, symlinks=True)
    dst_repo = dst_ws / "repo"
    for fix_fn in apply_fixes:
        fix_fn(dst_repo)


def _rewrite_script_paths(script_copy: Path, orig_ws: Path, tmp_ws: Path) -> None:
    """Redirect any hardcoded references to `orig_ws` (resolved or symlinked, e.g. /var vs /private/var) to `tmp_ws`."""
    try:
        text = script_copy.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    resolved = str(orig_ws.resolve())
    candidates = {str(orig_ws), resolved}
    if resolved.startswith("/private/"):
        candidates.add(resolved.removeprefix("/private"))
    updated = text
    # Replace longest paths first so /private/var/... is replaced cleanly before /var/...
    for old in sorted((c for c in candidates if c), key=len, reverse=True):
        if old in updated:
            updated = updated.replace(old, str(tmp_ws))
    if updated != text:
        script_copy.write_text(updated, encoding="utf-8")


def _build_script_command(script_copy: Path) -> list[str]:
    if script_copy.suffix == ".sh":
        return ["bash", str(script_copy)]
    if script_copy.suffix in (".mjs", ".js", ".ts", ".mts"):
        return ["node", str(script_copy)]
    if script_copy.suffix == ".py":
        try:
            src = script_copy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            src = ""
        # Handle unittest.TestCase files saved without `unittest.main()` (works even for absolute or hyphenated paths)
        has_testcase = bool(re.search(r"\bTestCase\b", src))
        has_main_call = "unittest.main" in src
        if has_testcase and not has_main_call:
            ut_runner = (
                "import importlib.util, pathlib, sys, unittest; "
                "p = pathlib.Path(sys.argv[1]); "
                "spec = importlib.util.spec_from_file_location('repro_ut', p); "
                "mod = importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(mod); "
                "suite = unittest.defaultTestLoader.loadTestsFromModule(mod); "
                "assert suite.countTestCases() > 0, 'no unittest cases found'; "
                "res = unittest.TextTestRunner(verbosity=0).run(suite); "
                "sys.exit(0 if res.wasSuccessful() else 1)"
            )
            return [sys.executable, "-B", "-c", ut_runner, str(script_copy)]
        # Handle pytest-style bare `def test_...()` files without a top-level entry point
        has_test_defs = bool(re.search(r"^\s*def\s+test_[A-Za-z0-9_]*\s*\(", src, re.M))
        has_top_level_main = bool(re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", src))
        if has_test_defs and not has_testcase and not has_top_level_main:
            runner = (
                "import importlib.util, inspect, pathlib, sys, tempfile; "
                "p = pathlib.Path(sys.argv[1]); "
                "spec = importlib.util.spec_from_file_location('repro_mod', p); "
                "mod = importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(mod); "
                "fns = [fn for name, fn in inspect.getmembers(mod, inspect.isfunction) if name.startswith('test_')]; "
                "assert fns, 'no test_* functions found'; "
                "\n"
                "for fn in fns:\n"
                "    sig = inspect.signature(fn)\n"
                "    if len(sig.parameters) == 0:\n"
                "        fn()\n"
                "    elif list(sig.parameters) == ['tmp_path']:\n"
                "        with tempfile.TemporaryDirectory() as td:\n"
                "            fn(pathlib.Path(td))\n"
                "    else:\n"
                "        raise TypeError(f'unsupported fixture params for {fn.__name__}: {list(sig.parameters)}')\n"
            )
            return [sys.executable, "-B", "-c", runner, str(script_copy)]
        return [sys.executable, "-B", str(script_copy)]
    return [str(script_copy)]


def _run_script_on_variant(
    orig_ws: Path,
    rel_script: Path,
    tmp_ws: Path,
    *,
    cwd_mode: str = "ws",
    attempts: int = 1,
    timeout: float = 15.0,
) -> tuple[bool, str]:
    """Run `rel_script` inside `tmp_ws`. Returns (passed_all_attempts, last_output)."""
    script_copy = tmp_ws / rel_script
    if not script_copy.is_file():
        return False, f"script missing in variant copy: {rel_script}"
    _rewrite_script_paths(script_copy, orig_ws, tmp_ws)
    argv = _build_script_command(script_copy)
    repo_dir = tmp_ws / "repo"
    python_paths = [str(repo_dir)]
    if (repo_dir / "src").is_dir():
        python_paths.append(str(repo_dir / "src"))
    if os.environ.get("PYTHONPATH"):
        python_paths.append(os.environ["PYTHONPATH"])
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(python_paths),
        "PYTHONDONTWRITEBYTECODE": "1",
        "ASTACK_REPO_DIR": str(repo_dir),
    }
    cwd = repo_dir if cwd_mode == "repo" else tmp_ws
    last_out = ""
    for _ in range(max(1, attempts)):
        try:
            proc = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
            last_out = (proc.stderr.strip() or proc.stdout.strip())[:240]
            if proc.returncode != 0:
                return False, last_out or f"exit {proc.returncode}"
        except subprocess.TimeoutExpired:
            return False, f"timed out after {timeout}s"
        except OSError as exc:
            return False, str(exc)
    return True, last_out or "ok"


def verify_reproductions(
    ws: Path,
    bugs: list[PlantedBug],
    *,
    min_proven: int = 1,
    require_all: tuple[str, ...] = (),
    require_any: tuple[str, ...] = (),
    allow_zero_scripts_when_no_bugs: bool = True,
) -> tuple[int, dict]:
    """Run full repo-untouched + behavioral reproduction verification.

    Returns (exit_code, report_dict). Always emits a structured `PROVEN_BUGS_JSON: ...` line
    for downstream consumers (including `scripts/eval.py --calibrate`).
    """
    ws_resolved = ws.resolve()
    ok_repo, repo_msg = check_repo_untouched(ws_resolved)
    if not ok_repo:
        report = {
            "repo_untouched": False,
            "error": repo_msg,
            "detected": [],
            "missed": [b.bug_id for b in bugs],
            "detected_count": 0,
            "planted_count": len(bugs),
        }
        print(f"FAIL: {repo_msg}", file=sys.stderr)
        print("PROVEN_BUGS_JSON: " + json.dumps(report))
        return 1, report

    scripts = discover_repro_scripts(ws_resolved)
    rel_scripts = [s.relative_to(ws_resolved) for s in scripts]

    # Clean-repo case (0 planted bugs): ensure no saved reproduction falsely fails on clean code
    if not bugs:
        false_failures: list[dict[str, str]] = []
        if rel_scripts:
            with tempfile.TemporaryDirectory(prefix="astack-verify-clean-") as td:
                tmp_ws = Path(td) / "ws"
                _clone_workspace_for_variant(ws_resolved, tmp_ws, [])
                for rel in rel_scripts:
                    passed, out = _run_script_on_variant(ws_resolved, rel, tmp_ws, cwd_mode="ws", attempts=1)
                    if not passed:
                        passed_repo, out_repo = _run_script_on_variant(ws_resolved, rel, tmp_ws, cwd_mode="repo", attempts=1)
                        if not passed_repo:
                            false_failures.append({"script": str(rel), "error": out_repo or out})
        report = {
            "repo_untouched": True,
            "scripts_checked": [str(r) for r in rel_scripts],
            "false_failures": false_failures,
            "detected": [],
            "missed": [],
            "detected_count": 0,
            "planted_count": 0,
        }
        if false_failures:
            print(f"FAIL: saved reproduction(s) failed on clean code: {false_failures}", file=sys.stderr)
            print("PROVEN_BUGS_JSON: " + json.dumps(report))
            return 1, report
        print(f"PASS: repo clean and untouched ({len(rel_scripts)} script(s) checked, 0 false failures)")
        print("PROVEN_BUGS_JSON: " + json.dumps(report))
        return 0, report

    if not rel_scripts:
        report = {
            "repo_untouched": True,
            "scripts_checked": [],
            "valid_repros": [],
            "failed_on_fixed": [],
            "passed_on_buggy": [],
            "detected": [],
            "missed": [b.bug_id for b in bugs],
            "detected_count": 0,
            "planted_count": len(bugs),
            "by_bug": {},
        }
        print("FAIL: no saved reproduction scripts found in workspace (outside repo/)", file=sys.stderr)
        print("PROVEN_BUGS_JSON: " + json.dumps(report))
        return 1, report

    all_fixes = [b.apply_fix for b in bugs]
    max_buggy_attempts = max(b.attempts for b in bugs)
    valid_repros: list[tuple[Path, str]] = []  # (rel_script, working_cwd_mode)
    failed_on_fixed: list[dict[str, str]] = []
    passed_on_buggy: list[str] = []
    by_bug: dict[str, list[str]] = {b.bug_id: [] for b in bugs}

    with tempfile.TemporaryDirectory(prefix="astack-verify-repros-") as td:
        td_p = Path(td)
        fixed_ws = td_p / "all_fixed"
        buggy_ws = td_p / "buggy"
        _clone_workspace_for_variant(ws_resolved, fixed_ws, all_fixes)
        _clone_workspace_for_variant(ws_resolved, buggy_ws, [])

        for rel in rel_scripts:
            # Determine working cwd_mode via all_fixed (must exit 0 on cleanly fixed repo)
            cwd_mode = ""
            ok_fix_ws, out_fix_ws = _run_script_on_variant(ws, rel, fixed_ws, cwd_mode="ws", attempts=1)
            if ok_fix_ws:
                cwd_mode = "ws"
            else:
                ok_fix_repo, out_fix_repo = _run_script_on_variant(ws, rel, fixed_ws, cwd_mode="repo", attempts=1)
                if ok_fix_repo:
                    cwd_mode = "repo"
                else:
                    failed_on_fixed.append({"script": str(rel), "error": out_fix_ws or out_fix_repo})
                    continue

            # Must FAIL on the buggy repo
            ok_buggy, _ = _run_script_on_variant(
                ws, rel, buggy_ws, cwd_mode=cwd_mode, attempts=max_buggy_attempts
            )
            if ok_buggy:
                passed_on_buggy.append(str(rel))
                continue

            valid_repros.append((rel, cwd_mode))

        # Leave-one-bug-in attribution: if script passes on all_fixed and fails on all_fixed_except[B], it proves B
        if valid_repros:
            if len(bugs) == 1:
                # Single planted bug: failing on buggy and passing on all_fixed already proves it!
                by_bug[bugs[0].bug_id] = [str(rel) for rel, _ in valid_repros]
            else:
                for b in bugs:
                    other_fixes = [ob.apply_fix for ob in bugs if ob.bug_id != b.bug_id]
                    except_ws = td_p / f"except_{b.bug_id}"
                    _clone_workspace_for_variant(ws_resolved, except_ws, other_fixes)
                    for rel, cwd_mode in valid_repros:
                        passed_with_b, _ = _run_script_on_variant(
                            ws, rel, except_ws, cwd_mode=cwd_mode, attempts=b.attempts
                        )
                        if not passed_with_b:
                            by_bug[b.bug_id].append(str(rel))

    detected = [b.bug_id for b in bugs if by_bug[b.bug_id]]
    missed = [b.bug_id for b in bugs if not by_bug[b.bug_id]]
    report = {
        "repo_untouched": True,
        "scripts_checked": [str(r) for r in rel_scripts],
        "valid_repros": [str(r) for r, _ in valid_repros],
        "failed_on_fixed": failed_on_fixed,
        "passed_on_buggy": passed_on_buggy,
        "detected": detected,
        "missed": missed,
        "detected_count": len(detected),
        "planted_count": len(bugs),
        "by_bug": {k: v for k, v in by_bug.items() if v},
    }

    failures: list[str] = []
    if len(detected) < min_proven:
        failures.append(f"proven {len(detected)}/{len(bugs)} planted bugs (need >= {min_proven}); missed={missed}")
    for req in require_all:
        if req not in detected:
            failures.append(f"required bug {req!r} was not proven by any saved reproduction")
    if require_any and not any(req in detected for req in require_any):
        failures.append(f"none of required bugs {list(require_any)} was proven by any saved reproduction")

    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        if failed_on_fixed:
            print(f"  scripts that failed on fixed repo: {failed_on_fixed}", file=sys.stderr)
        print("PROVEN_BUGS_JSON: " + json.dumps(report))
        return 1, report

    print(f"PASS: repo untouched; objectively proven {len(detected)}/{len(bugs)} planted bug(s) ({', '.join(detected)})")
    print("PROVEN_BUGS_JSON: " + json.dumps(report))
    return 0, report

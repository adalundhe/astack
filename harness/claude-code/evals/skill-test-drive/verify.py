#!/usr/bin/env python3
"""Objective post-run verifier for skill-test-drive."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _find_driver_script(ws: Path) -> Path | None:
    preferred = [
        ws / "program" / "drive-todo.py",
        ws / "program" / "drive_todo.py",
        ws / "repo" / "scripts" / "drive_todo.py",
        ws / "repo" / "scripts" / "drive-todo.py",
    ]
    for cand in preferred:
        if cand.is_file():
            return cand.resolve()
    for base in (ws / "program", ws / "repo"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*drive*todo*")):
            if p.is_file() and p.suffix in (".py", ".sh") and "__pycache__" not in p.parts:
                return p.resolve()
    return None


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    base_sha_file = ws / "program" / "base_sha.txt"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not base_sha_file.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/base_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    base_sha = base_sha_file.read_text(encoding="utf-8").strip()
    buggy_cli = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/todo_cli.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # 1. Executable driver script exists, covers all 4 flows, and runs clean
    driver = _find_driver_script(ws)
    if driver is None:
        checks.append(("driver-script-exists", False, "no driver script found at program/drive-todo.py or repo/scripts/drive_todo.py"))
        checks.append(("driver-script-runs", False, "skipped: driver script missing"))
    else:
        is_exec = os.access(driver, os.X_OK)
        src = driver.read_text(encoding="utf-8", errors="replace").lower()
        covers_flows = (
            "add" in src
            and "list" in src
            and "complete" in src
            and ("todo_cli" in src or "todo-cli" in src)
        )
        checks.append((
            "driver-script-exists",
            is_exec and covers_flows,
            f"driver={driver.relative_to(ws)} executable={is_exec} covers_flows={covers_flows}",
        ))
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        run_cmd = [str(driver)] if is_exec else [sys.executable, "-B", str(driver)]
        proc = subprocess.run(run_cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=30)
        checks.append((
            "driver-script-runs",
            proc.returncode == 0,
            f"driver exited 0 ({driver.name})"
            if proc.returncode == 0
            else f"driver exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:240]}",
        ))

    # 2. Direct end-to-end CLI flow verification (add, list, complete, invalid ID)
    cli_path = (repo / "src" / "todo_cli.py").resolve()
    with tempfile.TemporaryDirectory(prefix="astack-todo-verify-") as td:
        db = Path(td) / "todos.json"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, "-B", str(cli_path), "--db", str(db), *args],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )

        r_add = _run_cli("add", "Ship release")
        r_list1 = _run_cli("list")
        r_done = _run_cli("complete", "1")
        r_list2 = _run_cli("list")
        r_bad = _run_cli("complete", "999")

        happy_ok = (
            r_add.returncode == 0
            and r_list1.returncode == 0
            and "Ship release" in r_list1.stdout
            and r_done.returncode == 0
            and r_list2.returncode == 0
            and "[x]" in r_list2.stdout.lower()
        )
        checks.append((
            "cli-happy-flows",
            happy_ok,
            "add -> list -> complete -> list verified"
            if happy_ok
            else f"happy flow failed: add={r_add.returncode}, done={r_done.returncode}, list2={r_list2.stdout!r}",
        ))

        bad_combined = (r_bad.stdout + "\n" + r_bad.stderr).strip()
        bad_clean = (
            r_bad.returncode != 0
            and "Traceback" not in bad_combined
            and "KeyError" not in bad_combined
            and bool(bad_combined)
        )
        checks.append((
            "cli-invalid-id-clean-error",
            bad_clean,
            f"missing ID exited {r_bad.returncode} cleanly: {bad_combined[:120]!r}"
            if bad_clean
            else f"missing ID handling broken (rc={r_bad.returncode}): {bad_combined[:200]!r}",
        ))

    # 3. Unit tests pass
    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    # 4. Resilient mutation check: restoring original KeyError-buggy todo_cli.py MUST fail unittest
    mut_ok, mut_detail = _eval_kit.check_mutation_caught(
        repo, "src/todo_cli.py", lambda _: buggy_cli
    )
    checks.append(("mutation-missing-id-caught", mut_ok, mut_detail))

    # 5. Gates intact
    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    sec_hits = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

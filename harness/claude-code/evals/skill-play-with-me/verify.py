#!/usr/bin/env python3
"""Executable verifier for `skill-play-with-me`."""
from __future__ import annotations

import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    demo_path = (ws / "program" / "prototype" / "demo.py").resolve()
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_before_ok, clean_before_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean-before", clean_before_ok, clean_before_detail))

    if not demo_path.is_file():
        checks.append(("prototype-exists", False, "missing program/prototype/demo.py"))
        return _eval_kit.report_and_exit(checks)
    checks.append(("prototype-exists", True, str(demo_path.relative_to(ws))))

    try:
        py_compile.compile(str(demo_path), doraise=True)
        checks.append(("py-compile", True, "demo.py compiled"))
    except py_compile.PyCompileError as exc:
        checks.append(("py-compile", False, f"compile failed: {exc}"))
        return _eval_kit.report_and_exit(checks)

    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    undo_proc = subprocess.run(
        [sys.executable, "-B", str(demo_path), "--scenario", "undo"],
        cwd=ws,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
    )
    confirm_proc = subprocess.run(
        [sys.executable, "-B", str(demo_path), "--scenario", "confirm"],
        cwd=ws,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
    )

    undo_out = undo_proc.stdout.strip()
    confirm_out = confirm_proc.stdout.strip()

    checks.append((
        "scenario-undo-runs",
        undo_proc.returncode == 0 and bool(undo_out),
        f"exit 0 ({len(undo_out.splitlines())} lines)"
        if (undo_proc.returncode == 0 and undo_out)
        else f"exit={undo_proc.returncode}, stderr={undo_proc.stderr.strip()[:140]}",
    ))
    checks.append((
        "scenario-confirm-runs",
        confirm_proc.returncode == 0 and bool(confirm_out),
        f"exit 0 ({len(confirm_out.splitlines())} lines)"
        if (confirm_proc.returncode == 0 and confirm_out)
        else f"exit={confirm_proc.returncode}, stderr={confirm_proc.stderr.strip()[:140]}",
    ))

    distinct_ok = (
        bool(undo_out)
        and bool(confirm_out)
        and undo_out != confirm_out
        and bool(re.search(r"\b(undo|restor\w*|revert\w*|pending)\b", undo_out, re.I))
        and bool(re.search(r"\b(confirm\w*|y/n|cancel\w*|prompt|awaiting)\b", confirm_out, re.I))
    )
    checks.append((
        "scenarios-distinct-and-concrete",
        distinct_ok,
        "undo and confirm scenarios produce distinct flow-specific outputs"
        if distinct_ok
        else f"undo_len={len(undo_out)}, confirm_len={len(confirm_out)}, equal={undo_out == confirm_out}",
    ))

    clean_after_ok, clean_after_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean-after-exec", clean_after_ok, clean_after_detail))

    demo_src = demo_path.read_text(encoding="utf-8", errors="replace")
    sec_hits = _eval_kit.check_no_secrets([demo_src, undo_out, confirm_out, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

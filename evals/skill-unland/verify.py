#!/usr/bin/env python3
"""Objective post-run verifier for skill-unland."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _git_out(repo: Path, *args: str) -> str:
    proc = _git(repo, *args)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    commit_a = (ws / "program" / "commit_a.txt").read_text(encoding="utf-8").strip()
    commit_b = (ws / "program" / "commit_b.txt").read_text(encoding="utf-8").strip()
    commit_c = (ws / "program" / "commit_c.txt").read_text(encoding="utf-8").strip()
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    # Commit C must remain an ancestor of HEAD (history preserved; never git reset --hard dropping C)
    anc_c = _git(repo, "merge-base", "--is-ancestor", commit_c, "HEAD").returncode == 0
    head_sha = _git_out(repo, "rev-parse", "HEAD").strip()
    new_commits = int(_git_out(repo, "rev-list", "--count", f"{commit_c}..HEAD").strip()) if anc_c else 0
    checks.append((
        "history-and-commit-c-preserved",
        anc_c and head_sha != commit_c and 1 <= new_commits <= 2,
        f"commit C ({commit_c[:8]}) preserved in ancestry with {new_commits} revert commit(s) on top"
        if (anc_c and head_sha != commit_c and 1 <= new_commits <= 2)
        else f"anc_c={anc_c}, head={head_sha[:8]}, commit_c={commit_c[:8]}, commits_after_c={new_commits}",
    ))

    # Revert commit message references revert / commit B
    log_after_c = _git_out(repo, "log", "--format=%B", f"{commit_c}..HEAD") if anc_c else ""
    revert_logged = ("revert" in log_after_c.lower()) or (commit_b[:7] in log_after_c)
    checks.append((
        "revert-commit-recorded",
        revert_logged,
        "revert commit message recorded on top of commit C"
        if revert_logged
        else f"expected revert commit message referencing commit B ({commit_b[:7]}), got: {log_after_c[:120]!r}",
    ))

    # src/rate_limit.py matches Commit A (Commit B reverted)
    orig_rl = _git_out(repo, "show", f"{commit_a}:src/rate_limit.py")
    curr_rl = (repo / "src" / "rate_limit.py").read_text(encoding="utf-8") if (repo / "src" / "rate_limit.py").is_file() else ""
    checks.append((
        "commit-b-reverted",
        curr_rl == orig_rl,
        "src/rate_limit.py restored to pre-regression state"
        if curr_rl == orig_rl
        else "src/rate_limit.py does not match commit A",
    ))

    # Commit C's docs/API.md and README.md remain completely intact
    orig_api = _git_out(repo, "show", f"{commit_c}:docs/API.md")
    orig_readme = _git_out(repo, "show", f"{commit_c}:README.md")
    curr_api = (repo / "docs" / "API.md").read_text(encoding="utf-8") if (repo / "docs" / "API.md").is_file() else ""
    curr_readme = (repo / "README.md").read_text(encoding="utf-8") if (repo / "README.md").is_file() else ""
    docs_intact = (curr_api == orig_api) and (curr_readme == orig_readme)
    checks.append((
        "commit-c-docs-intact",
        docs_intact,
        "docs/API.md and README.md from commit C preserved intact"
        if docs_intact
        else "docs/API.md or README.md from commit C was modified or dropped",
    ))

    ok_ut, msg_ut = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_gates, msg_gates = _eval_kit.check_gates_intact(repo, base_ref=commit_a)
    checks.append(("gates-intact", ok_gates, msg_gates))

    sec = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

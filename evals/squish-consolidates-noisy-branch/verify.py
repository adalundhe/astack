#!/usr/bin/env python3
"""Objective post-run verifier for squish-consolidates-noisy-branch."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def _git(repo: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return res.stdout.strip()


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()
    pre_tree = (ws / "program" / "pre_squish_tree.txt").read_text(encoding="utf-8").strip()

    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "feat/retry-jitter":
        print(f"FAIL: expected branch feat/retry-jitter, got {branch}", file=sys.stderr)
        return 1
    if _git(repo, "rev-parse", "main") != base_sha:
        print("FAIL: main branch was modified", file=sys.stderr)
        return 1

    count = int(_git(repo, "rev-list", "--count", f"{base_sha}..HEAD"))
    if count < 1 or count > 2:
        print(f"FAIL: expected 1..2 consolidated commits, got {count}", file=sys.stderr)
        return 1

    cur_tree = _git(repo, "rev-parse", "HEAD^{tree}")
    if cur_tree != pre_tree:
        print(f"FAIL: squished tree {cur_tree} differs from pre-squish tree {pre_tree}", file=sys.stderr)
        return 1

    log_text = _git(repo, "log", "--format=%an <%ae>%n%B", f"{base_sha}..HEAD")
    if "bob@example.invalid" not in log_text.lower():
        print("FAIL: contributor credit for bob@example.invalid was dropped", file=sys.stderr)
        return 1

    ut = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(repo / "tests")],
        capture_output=True, text=True,
    )
    if ut.returncode != 0:
        print(f"FAIL: tests failed:\n{ut.stdout}\n{ut.stderr}", file=sys.stderr)
        return 1

    print(f"PASS: consolidated 6 commits -> {count}, tree identical, Bob's credit preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Objective post-run verifier for find-it-and-fix-it-bug.

Checks:
1. Unit tests pass on fixed repo.
2. Real 120-event workload produces exact independently computed oracle totals.
3. Red-first anti-tautology: the agent's tests FAIL when run against original main's src/processor.py.
4. Zero leftover *_DEBUG_*.* artifacts in repo/.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


def independent_oracle(events: list[dict]) -> tuple[dict[str, int], int]:
    totals: dict[str, int] = defaultdict(int)
    skipped = 0
    for ev in events:
        amount = int(ev["amount_cents"])
        if amount <= 0:
            skipped += 1
            continue
        kind = str(ev["kind"])
        acct = str(ev["account"])
        if kind == "charge":
            totals[acct] += amount
        elif kind == "retry":
            totals[acct] += amount * 90 // 100
        elif kind == "refund":
            totals[acct] -= amount
    return dict(sorted(totals.items())), skipped


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    events_path = ws / "program" / "billing_events.json"
    main_sha = (ws / "program" / "main_sha.txt").read_text(encoding="utf-8").strip()

    # 1. Zero leftover debug captures in repo/
    leftovers = list(repo.rglob("*_DEBUG_*.*"))
    if leftovers:
        print(f"FAIL: leftover debug artifacts in repo/: {leftovers}", file=sys.stderr)
        return 1

    # 2. Tests pass on fixed repo
    test_run = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(repo / "tests")],
        capture_output=True, text=True,
    )
    if test_run.returncode != 0:
        print(f"FAIL: unit tests failed after fix:\n{test_run.stdout}\n{test_run.stderr}", file=sys.stderr)
        return 1

    # 3. Real 120-event workload matches independent oracle
    cli_run = subprocess.run(
        [sys.executable, "-B", str(repo / "src" / "cli.py"), str(events_path)],
        capture_output=True, text=True,
    )
    if cli_run.returncode != 0:
        print(f"FAIL: cli.py exited {cli_run.returncode}: {cli_run.stderr}", file=sys.stderr)
        return 1
    actual = json.loads(cli_run.stdout)
    expected_totals, expected_skipped = independent_oracle(json.loads(events_path.read_text(encoding="utf-8")))
    if actual.get("totals") != expected_totals or actual.get("skipped") != expected_skipped:
        print(
            f"FAIL: workload output mismatch.\nExpected skipped={expected_skipped}, totals={expected_totals}\n"
            f"Actual={actual}",
            file=sys.stderr,
        )
        return 1

    # 4. Red-first anti-tautology check: agent's test suite MUST fail against original main src/processor.py
    with tempfile.TemporaryDirectory(prefix="astack-redcheck-") as td:
        tmp_repo = Path(td) / "repo"
        shutil.copytree(repo, tmp_repo)
        orig_proc = subprocess.run(
            ["git", "-C", str(repo), "show", f"{main_sha}:src/processor.py"],
            capture_output=True, text=True, check=True,
        ).stdout
        (tmp_repo / "src" / "processor.py").write_text(orig_proc, encoding="utf-8")
        red_run = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(tmp_repo / "tests")],
            capture_output=True, text=True,
        )
        if red_run.returncode == 0:
            print("FAIL: tests still passed against original buggy main src/processor.py (not red-first)", file=sys.stderr)
            return 1

    print("PASS: workload fixed, red-first behavior test verified, zero debug leftovers")
    return 0


if __name__ == "__main__":
    sys.exit(main())

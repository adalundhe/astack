#!/usr/bin/env python3
"""Objective post-run verifier for bugbash-investigates-and-proves-fix.

Checks:
1. Unit tests pass on fixed repo.
2. Both real bug scenarios from bug-report.md + linked-spec.md pass on fixed TransferLedger:
   - transient error is NOT cached, so retry succeeds once gateway recovers;
   - distinct tenants sharing an idempotency_key are strictly isolated;
   - same-tenant duplicate still replays cached ok receipt without double-charging.
3. Red-first anti-tautology: the agent's tests FAIL against original main's src/ledger.py.
4. program/pr-body.md exists, includes concrete verification/proof evidence, and leaks zero internal review labels.
5. Zero leftover *_DEBUG_*.* artifacts in repo/.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LEAK_RE = re.compile(
    r"\b(?:POOL EXHAUSTED|NOT ASSIGNED|STOPPED \(estimate\)|STOPPED \(saturated\)|"
    r"astack-review-ledger|Chapman|Jackknife)\b|coverage-map\.md"
)


def _load_ledger_cls(repo: Path):
    src_dir = str(repo / "src")
    sys.path.insert(0, src_dir)
    try:
        spec = importlib.util.spec_from_file_location("eval_ledger_under_test", repo / "src" / "ledger.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TransferLedger
    finally:
        if src_dir in sys.path:
            sys.path.remove(src_dir)


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    main_sha = (ws / "program" / "main_sha.txt").read_text(encoding="utf-8").strip()

    # 1. Zero leftover debug captures
    leftovers = list(repo.rglob("*_DEBUG_*.*"))
    if leftovers:
        print(f"FAIL: leftover debug artifacts in repo/: {leftovers}", file=sys.stderr)
        return 1

    # 2. Unit tests pass
    test_run = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(repo / "tests")],
        capture_output=True, text=True,
    )
    if test_run.returncode != 0:
        print(f"FAIL: unit tests failed:\n{test_run.stdout}\n{test_run.stderr}", file=sys.stderr)
        return 1

    # 3. Real behavior verification against TransferLedger
    TransferLedger = _load_ledger_cls(repo)

    # 3a. Transient error must not be cached
    attempts = {"n": 0}

    def flaky_gateway(tenant_id: str, amount_cents: int) -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("gateway timeout")
        return f"tx-{tenant_id}-{attempts['n']}"

    ledger1 = TransferLedger(flaky_gateway)
    r1 = ledger1.submit("tenant-a", "order-42", 2500)
    r2 = ledger1.submit("tenant-a", "order-42", 2500)
    r3 = ledger1.submit("tenant-a", "order-42", 2500)
    if r1.get("status") != "error" or r2.get("status") != "ok" or r3 != r2 or attempts["n"] != 2:
        print(f"FAIL: retry after transient error broken: r1={r1}, r2={r2}, r3={r3}, attempts={attempts['n']}", file=sys.stderr)
        return 1

    # 3b. Cross-tenant isolation with same idempotency_key
    calls = []

    def ok_gateway(tenant_id: str, amount_cents: int) -> str:
        calls.append((tenant_id, amount_cents))
        return f"tx-{tenant_id}-{len(calls)}"

    ledger2 = TransferLedger(ok_gateway)
    ta = ledger2.submit("tenant-a", "req-1", 1000)
    tb = ledger2.submit("tenant-b", "req-1", 2000)
    ta_again = ledger2.submit("tenant-a", "req-1", 1000)
    if ta.get("tenant_id") != "tenant-a" or tb.get("tenant_id") != "tenant-b" or ta_again != ta or len(calls) != 2:
        print(f"FAIL: tenant isolation broken: ta={ta}, tb={tb}, ta_again={ta_again}, calls={calls}", file=sys.stderr)
        return 1

    # 4. Red-first anti-tautology: agent's tests must FAIL against original main src/
    with tempfile.TemporaryDirectory(prefix="astack-bugbash-red-") as td:
        tmp_repo = Path(td) / "repo"
        shutil.copytree(repo, tmp_repo)
        for rel in ("src/ledger.py", "src/cache.py"):
            orig = subprocess.run(
                ["git", "-C", str(repo), "show", f"{main_sha}:{rel}"],
                capture_output=True, text=True, check=True,
            ).stdout
            (tmp_repo / rel).write_text(orig, encoding="utf-8")
        red_run = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(tmp_repo / "tests")],
            capture_output=True, text=True,
        )
        if red_run.returncode == 0:
            print("FAIL: tests still passed against original buggy main src/ (not red-first)", file=sys.stderr)
            return 1

    # 5. PR body exists, contains proof/verification evidence, and leaks zero internal ledger terms
    pr_body_path = ws / "program" / "pr-body.md"
    if not pr_body_path.is_file():
        print("FAIL: program/pr-body.md was not created", file=sys.stderr)
        return 1
    pr_text = pr_body_path.read_text(encoding="utf-8").strip()
    if len(pr_text) < 80:
        print("FAIL: program/pr-body.md is too short to contain real proof/evidence", file=sys.stderr)
        return 1
    if LEAK_RE.search(pr_text):
        print("FAIL: program/pr-body.md leaked internal review-ledger jargon", file=sys.stderr)
        return 1

    print("PASS: bugbash fixed both root causes, red-first tests verified, PR body with proof written cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Executable verifier for `skill-formal-validate`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_SAFETY_REPLAY_PROBE = r'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from lease import LeaseManager, LeaseState

mgr = LeaseManager()
t1 = mgr.acquire("c1", now=0, ttl=2)
assert t1 is not None, "c1 acquire failed"
mgr.expire_check(now=2)
assert mgr.state == LeaseState.EXPIRED, f"expected EXPIRED, got {mgr.state}"
t2 = mgr.acquire("c2", now=2, ttl=3)
assert t2 is not None and t2 != t1, f"c2 acquire failed: {t2}"
assert mgr.renew("c1", token=t1, now=3, ttl=3) is False, "expired c1 must not renew while c2 holds lease"
assert len(mgr.active_holders(now=3)) <= 1, f"mutual exclusion broken: {mgr.active_holders(3)}"
assert mgr.active_holders(now=3) == {"c2"}, f"expected only c2 active, got {mgr.active_holders(3)}"

# Also verify expired single client cannot renew after its own lease expired while IDLE/EXPIRED
mgr2 = LeaseManager()
t3 = mgr2.acquire("c1", now=0, ttl=2)
assert mgr2.renew("c1", token=t3, now=2, ttl=2) is False, "expired lease must not self-renew"
print("OK")
'''


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _validate_counterexample(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "counterexample.json is not a JSON object"
    steps = data.get("steps", data.get("trace"))
    if not isinstance(steps, list) or len(steps) < 3:
        return False, f"counterexample must include >= 3 steps, got {type(steps).__name__} len={len(steps) if isinstance(steps, list) else 0}"
    violated = data.get("violated", True)
    if violated is not True:
        return False, f"expected violated=true on buggy model counterexample, got {violated!r}"
    joined = json.dumps(data).lower()
    mentions_renew = "renew" in joined
    mentions_clients = ("c1" in joined and "c2" in joined) or ("holder" in joined)
    if not (mentions_renew and mentions_clients):
        return False, "counterexample trace does not capture the stale-holder renew scenario"
    return True, f"counterexample recorded with {len(steps)} step(s)"


def _run_checker(ws: Path, checker: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(checker)],
        cwd=ws,
        capture_output=True,
        text=True,
        timeout=25,
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checker = ws / "program" / "check_model.py"
    ce_path = ws / "program" / "counterexample.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, "missing ./repo"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    buggy_lease = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/lease.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    raw_ce = ""
    if ce_path.is_file():
        raw_ce = ce_path.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = json.loads(raw_ce)
        except json.JSONDecodeError as exc:
            checks.append(("counterexample-valid", False, f"invalid JSON: {exc}"))
        else:
            ok_ce, ce_msg = _validate_counterexample(parsed)
            checks.append(("counterexample-valid", ok_ce, ce_msg))
    else:
        checks.append(("counterexample-valid", False, "missing program/counterexample.json"))

    if checker.is_file():
        fixed_run = _run_checker(ws, checker)
        checks.append((
            "model-checker-passes-fixed-code",
            fixed_run.returncode == 0,
            "exhaustive check passed on fixed code (exit 0)"
            if fixed_run.returncode == 0
            else f"exit {fixed_run.returncode}: {(fixed_run.stderr.strip() or fixed_run.stdout.strip())[:220]}",
        ))

        # Prove checker is not vacuous: revert src/lease.py to buggy root commit temporarily and confirm checker fails!
        lease_file = repo / "src" / "lease.py"
        fixed_lease = lease_file.read_text(encoding="utf-8")
        try:
            lease_file.write_text(buggy_lease, encoding="utf-8")
            buggy_run = _run_checker(ws, checker)
        finally:
            lease_file.write_text(fixed_lease, encoding="utf-8")
        checks.append((
            "model-checker-catches-buggy-root",
            buggy_run.returncode != 0,
            f"buggy model caught (exit {buggy_run.returncode})"
            if buggy_run.returncode != 0
            else "model checker exited 0 on buggy root commit (vacuous check)",
        ))
    else:
        checks.append(("model-checker-passes-fixed-code", False, "missing program/check_model.py"))
        checks.append(("model-checker-catches-buggy-root", False, "missing program/check_model.py"))

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _SAFETY_REPLAY_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "mutual-exclusion-behavior-probe",
        probe.returncode == 0,
        "stale renew rejected and active_holders <= 1"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:220],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/lease.py", lambda _: buggy_lease)
    checks.append(("mutation-caught-by-tests", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text, raw_ce]
    if checker.is_file():
        texts.append(checker.read_text(encoding="utf-8", errors="replace"))
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Executable verifier for `rule-fail-safely`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


_BEHAVIOR_PROBE = r'''
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
import gateway

results = {}

# 1. Explicit finite timeout on fetch and submit
seen_timeouts = []
def ok_transport(method, path, timeout):
    seen_timeouts.append((method, timeout))
    return (200, {"method": method, "path": path})

c_ok = gateway.UpstreamClient(ok_transport, timeout_s=0.75)
assert c_ok.fetch("/a") == {"method": "GET", "path": "/a"}
assert c_ok.submit("/b", {"x": 1}) == {"method": "POST", "path": "/b"}
assert all(isinstance(t, (int, float)) and 0 < t <= 0.75 for _, t in seen_timeouts), f"invalid timeouts: {seen_timeouts}"
results["timeouts_ok"] = True

# 2. Bounded retries + exponential backoff with jitter
def run_failing_sequence(seed):
    calls = []
    sleeps = []
    def failing_transport(method, path, timeout):
        calls.append((method, path, timeout))
        if len(calls) > 20:
            raise RuntimeError("unbounded retry loop exceeded 20 calls")
        return (503, {"error": "unavailable"})

    client = gateway.UpstreamClient(
        failing_transport,
        timeout_s=0.5,
        max_retries=3,
        base_backoff_s=0.05,
        max_backoff_s=0.4,
        retry_budget=10,
        sleep_fn=sleeps.append,
        rng=random.Random(seed),
    )
    raised = False
    try:
        client.fetch("/flaky")
    except Exception as exc:
        if "unbounded retry loop" in str(exc):
            raise
        raised = True
    assert raised, "fetch did not raise after exhausting retries"
    assert 2 <= len(calls) <= 4, f"expected 2..4 calls for max_retries=3, got {len(calls)}"
    assert len(sleeps) == len(calls) - 1, f"expected {len(calls) - 1} sleeps, got {len(sleeps)}"
    assert all(isinstance(s, (int, float)) and 0 <= s <= 0.4 + 1e-6 for s in sleeps), f"backoff out of bounds: {sleeps}"
    assert any(s > 0 for s in sleeps), f"zero backoff sleeps: {sleeps}"
    return sleeps

s1 = run_failing_sequence(101)
s2 = run_failing_sequence(202)
s3 = run_failing_sequence(303)
assert len({tuple(round(x, 6) for x in s) for s in (s1, s2, s3)}) >= 2, f"no jitter detected across seeds: {s1}, {s2}, {s3}"
results["jitter_backoff_ok"] = True

# 3. Retry budget bounds retries across sustained outage burst
burst_calls = [0]
def outage_transport(method, path, timeout):
    burst_calls[0] += 1
    if burst_calls[0] > 40:
        raise RuntimeError("retry budget not enforced (>40 calls)")
    raise TimeoutError("blackholed")

c_budget = gateway.UpstreamClient(
    outage_transport,
    timeout_s=0.25,
    max_retries=3,
    base_backoff_s=0.01,
    max_backoff_s=0.1,
    retry_budget=4,
    sleep_fn=lambda _: None,
    rng=random.Random(7),
)
for idx in range(8):
    try:
        c_budget.fetch(f"/item-{idx}")
        raise AssertionError("expected failure on outage")
    except Exception as exc:
        if "retry budget not enforced" in str(exc):
            raise
# 8 initial attempts + at most 4 budgeted retries = at most 12 total calls
assert burst_calls[0] <= 12, f"retry budget exceeded: {burst_calls[0]} calls for 8 requests with budget=4"
results["retry_budget_ok"] = True

# 4. Non-idempotent submit never retries
post_calls = [0]
def failing_post(method, path, timeout):
    post_calls[0] += 1
    if post_calls[0] > 5:
        raise RuntimeError("submit retried non-idempotent POST")
    return (503, {"error": "down"})

c_post = gateway.UpstreamClient(
    failing_post,
    timeout_s=0.5,
    max_retries=3,
    retry_budget=5,
    sleep_fn=lambda _: None,
)
post_raised = False
try:
    c_post.submit("/charge", {"amount": 100})
except Exception:
    post_raised = True
assert post_raised, "submit did not raise on 503"
assert post_calls[0] == 1, f"submit must not retry non-idempotent POST, made {post_calls[0]} calls"
results["no_post_retry_ok"] = True

# 5. Liveness decoupled from DB; readiness handles errors and stalls within timeout
db_calls = [0]
def slow_broken_db():
    db_calls[0] += 1
    time.sleep(1.5)
    raise ConnectionError("db down")

health = gateway.HealthService(slow_broken_db)
t0 = time.monotonic()
live = health.liveness()
live_dt = time.monotonic() - t0
assert live.get("status") == "ok", f"liveness failed: {live}"
assert db_calls[0] == 0, f"liveness invoked db_ping {db_calls[0]} time(s)"
assert live_dt < 0.2, f"liveness took too long: {live_dt:.3f}s"

t1 = time.monotonic()
ready_slow = health.readiness(timeout_s=0.1)
ready_dt = time.monotonic() - t1
assert ready_slow.get("status") != "ready", f"readiness reported ready on stalled DB: {ready_slow}"
assert ready_dt < 0.6, f"readiness did not enforce timeout_s=0.1 (took {ready_dt:.3f}s)"

health_err = gateway.HealthService(lambda: (_ for _ in ()).throw(ConnectionError("conn refused")))
ready_err = health_err.readiness(timeout_s=0.2)
assert ready_err.get("status") != "ready", f"readiness reported ready on DB error: {ready_err}"

health_ok = gateway.HealthService(lambda: True)
assert health_ok.readiness(timeout_s=0.2).get("status") == "ready"
results["probes_ok"] = True

print(json.dumps(results))
'''


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    buggy_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/gateway.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # 1. Behavioral fault-injection probe
    try:
        probe = subprocess.run(
            [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if probe.returncode == 0:
            checks.append(("behavior-fault-injection", True, probe.stdout.strip()))
        else:
            detail = (probe.stderr.strip() or probe.stdout.strip() or f"exit {probe.returncode}")[:300]
            checks.append(("behavior-fault-injection", False, detail))
    except subprocess.TimeoutExpired:
        checks.append(("behavior-fault-injection", False, "timed out after 10s (unbounded wait or retry loop)"))

    # 2. Repo unit test suite
    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    # 3. Mutation check: re-inject original buggy gateway.py -> repo tests must fail
    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/gateway.py", lambda _: buggy_src)
    checks.append(("mutation-caught", mut_ok, mut_detail))

    # 4. Gates intact
    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    # 5. Secrets & internal jargon hygiene
    final_text = _eval_kit.final_text_from_env()
    sec_hits = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))
    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

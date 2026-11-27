#!/usr/bin/env python3
"""Objective post-run verifier for rule-event-driven."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _initial_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _check_no_sleep_calls(src_path: Path) -> tuple[bool, str]:
    if not src_path.is_file():
        return False, "src/job_runner.py missing"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "sleep":
                return False, f"sleep call `{ast.unparse(node)}` still present in src/job_runner.py"
            if isinstance(fn, ast.Name) and fn.id == "sleep":
                return False, f"sleep call `{ast.unparse(node)}` still present in src/job_runner.py"
    return True, "zero sleep calls in src/job_runner.py"


def _check_behavior(repo: Path) -> tuple[bool, str]:
    probe = r"""
import threading
import time
from src.job_runner import JobRunner

# Forbid any runtime time.sleep call during JobRunner execution
orig_sleep = time.sleep
def forbidden_sleep(*args, **kwargs):
    raise AssertionError(f"forbidden polling via time.sleep({args}, {kwargs})")

time.sleep = forbidden_sleep
runner = JobRunner()
try:
    # 1. Unknown job_id raises KeyError immediately
    try:
        runner.wait_for("does-not-exist", timeout=1.0)
    except KeyError:
        pass
    else:
        raise AssertionError("wait_for on unknown job_id did not raise KeyError")

    # 2. Duplicate job_id raises ValueError
    runner.submit("dup", lambda: "first")
    try:
        runner.submit("dup", lambda: "second")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate job_id did not raise ValueError")
    assert runner.wait_for("dup", timeout=2.0) == "first"

    # 3. Immediate wakeup on Event release (zero sleep polling)
    gate = threading.Event()
    runner.submit("gated", lambda: (gate.wait(5.0), "released")[1])
    released_at = [0.0]
    woke_at = [0.0]
    result_box = []
    def waiter():
        res = runner.wait_for("gated", timeout=5.0)
        woke_at[0] = time.monotonic()
        result_box.append(res)
    wt = threading.Thread(target=waiter)
    wt.start()
    orig_sleep(0.01)
    released_at[0] = time.monotonic()
    gate.set()
    wt.join(timeout=5.0)
    assert not wt.is_alive() and result_box == ["released"], f"gated wait failed: {result_box}"
    wake_latency = woke_at[0] - released_at[0]
    assert wake_latency < 0.5, f"slow wakeup latency {wake_latency:.4f}s (expected immediate event wakeup)"

    # 4. 25 sequential instant jobs finish rapidly without polling delay
    t0 = time.monotonic()
    for i in range(25):
        jid = f"fast-{i}"
        runner.submit(jid, lambda n=i: n * 3)
        assert runner.wait_for(jid, timeout=2.0) == i * 3
    batch_elapsed = time.monotonic() - t0
    assert batch_elapsed < 2.0, f"25 fast jobs took {batch_elapsed:.3f}s (expected < 2.0s without sleep polling)"

    # 5. Failure propagates original exception immediately
    def boom():
        raise ValueError("job exploded")
    runner.submit("failing", boom)
    try:
        runner.wait_for("failing", timeout=2.0)
    except ValueError as exc:
        assert "job exploded" in str(exc)
    else:
        raise AssertionError("failing job did not propagate ValueError")

    # 6. Timeout triggers promptly when blocked
    blocker = threading.Event()
    runner.submit("blocked", lambda: blocker.wait(5.0))
    try:
        try:
            runner.wait_for("blocked", timeout=0.05)
        except TimeoutError:
            pass
        else:
            raise AssertionError("blocked job did not raise TimeoutError")
    finally:
        blocker.set()
    runner.wait_for("blocked", timeout=2.0)

    # 7. wait_all gathers all results and respects unknown IDs
    g1, g2 = threading.Event(), threading.Event()
    runner.submit("a1", lambda: (g1.wait(5.0), 10)[1])
    runner.submit("a2", lambda: (g2.wait(5.0), 20)[1])
    g1.set()
    g2.set()
    assert runner.wait_all(["a1", "a2"], timeout=2.0) == {"a1": 10, "a2": 20}

    try:
        runner.wait_all(["a1", "missing-id"], timeout=1.0)
    except KeyError:
        pass
    else:
        raise AssertionError("wait_all with unknown job_id did not raise KeyError")
finally:
    runner.shutdown()
    time.sleep = orig_sleep

print(f"WAKE_OK latency_ms={wake_latency * 1000:.2f} batch25_ms={batch_elapsed * 1000:.1f}")
"""
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())[:400]
    return True, proc.stdout.strip().splitlines()[-1]


def _mutate_event_wait_regression(orig: str) -> str:
    return (
        orig
        + "\n\n# --- injected mutation: break wait_for timeout/unknown-job/sleep-free contract ---\n"
        "import time as _mut_time\n"
        "_orig_wait_for = JobRunner.wait_for\n"
        "def _mut_wait_for(self, job_id, timeout=None):\n"
        "    _mut_time.sleep(0)\n"
        "    try:\n"
        "        return _orig_wait_for(self, job_id, timeout=timeout)\n"
        "    except KeyError:\n"
        "        raise TimeoutError(f'timed out waiting for job {job_id}')\n"
        "    except TimeoutError:\n"
        "        return None\n"
        "JobRunner.wait_for = _mut_wait_for\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    base_sha = _initial_sha(repo)

    checks: list[tuple[str, bool, str]] = []
    ok_ast, msg_ast = _check_no_sleep_calls(repo / "src" / "job_runner.py")
    checks.append(("no-sleep-polling", ok_ast, msg_ast))

    ok_beh, msg_beh = _check_behavior(repo)
    checks.append(("behavior", ok_beh, msg_beh))

    ok_ut, msg_ut = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = _eval_kit.check_mutation_caught(repo, "src/job_runner.py", _mutate_event_wait_regression)
    checks.append(("mutation-caught", ok_mut, msg_mut))

    ok_gates, msg_gates = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", ok_gates, msg_gates))

    sec = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

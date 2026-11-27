#!/usr/bin/env python3
"""Executable verifier for `skill-clamber`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _validate_clamber_log(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "clamber_log.json is not a JSON object"

    baseline = data.get("baseline")
    if isinstance(baseline, dict):
        base_med = baseline.get("median_ms", baseline.get("p50_ms", baseline.get("mean_ms")))
    else:
        base_med = data.get("baseline_median_ms")
    if not isinstance(base_med, (int, float)) or isinstance(base_med, bool) or float(base_med) <= 0:
        return False, f"invalid baseline median_ms: {base_med!r}"
    base_med_f = float(base_med)

    steps = data.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        return False, f"expected >= 2 incremental steps in clamber_log.json, got {type(steps).__name__}"

    kept_steps: list[dict[str, Any]] = []
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, f"step[{idx}] is not an object"
        outcome = str(step.get("outcome", "")).lower()
        is_kept = outcome in ("kept", "keep", "accepted") or step.get("kept") is True
        if not is_kept:
            continue
        before = step.get("before_median_ms", step.get("before_ms"))
        after = step.get("after_median_ms", step.get("after_ms"))
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            return False, f"kept step[{idx}] missing numeric before/after median_ms"
        if float(after) <= 0 or float(after) >= float(before):
            return False, f"kept step[{idx}] did not improve: before={before}ms -> after={after}ms"
        if step.get("parity_verified") is not True:
            return False, f"kept step[{idx}] parity_verified is not true"
        if step.get("tests_passed") is not True:
            return False, f"kept step[{idx}] tests_passed is not true"
        kept_steps.append(step)

    if len(kept_steps) < 2:
        return False, f"expected >= 2 kept improving steps, found {len(kept_steps)}"

    first_after = float(kept_steps[0].get("after_median_ms", kept_steps[0].get("after_ms")))
    last_after = float(kept_steps[-1].get("after_median_ms", kept_steps[-1].get("after_ms")))
    if not (last_after < first_after < base_med_f):
        return False, (
            f"expected progressive improvement across steps "
            f"(baseline={base_med_f:.3f}ms, step1={first_after:.3f}ms, final={last_after:.3f}ms)"
        )

    return True, (
        f"baseline={base_med_f:.2f}ms -> step1={first_after:.2f}ms -> "
        f"final={last_after:.2f}ms across {len(kept_steps)} kept steps"
    )


def _verify_parity_and_speedup(repo: Path, base_src: str, workload_path: Path) -> tuple[bool, str]:
    probe = r'''
import json, statistics, sys, time, types
from pathlib import Path

repo = Path(sys.argv[1])
lines = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
base_src = sys.stdin.read()

base_mod = types.ModuleType("pipeline_base")
exec(compile(base_src, "<base:src/pipeline.py>", "exec"), base_mod.__dict__)

sys.path.insert(0, str(repo / "src"))
import pipeline as curr_mod

base_out = base_mod.process_events(lines)
curr_out = curr_mod.process_events(lines)
assert len(base_out) > 1000, f"unexpectedly small workload output: {len(base_out)}"
assert curr_out == base_out, "output parity mismatch against baseline"

# Edge cases: empty list, out-of-order key=value fields, duplicates
edge_lines = [
    "",
    "2026-11-26T10:00:01Z status=200 latency_ms=5 user=u9 req=e1 level=INFO",
    "2026-11-26T10:00:02Z status=500 latency_ms=99 user=u1 req=e1 level=ERROR",
    "bad timestamp level=INFO req=e2 user=u2 latency_ms=1 status=200",
]
assert curr_mod.process_events(edge_lines) == base_mod.process_events(edge_lines), "edge parity mismatch"

# Alternating timing (1 warmup + 3 measured rounds)
base_mod.process_events(lines)
curr_mod.process_events(lines)

base_ms, curr_ms = [], []
for r in range(3):
    order = ("base", "curr") if r % 2 == 0 else ("curr", "base")
    for side in order:
        fn = base_mod.process_events if side == "base" else curr_mod.process_events
        t0 = time.perf_counter()
        fn(lines)
        dt = (time.perf_counter() - t0) * 1000.0
        (base_ms if side == "base" else curr_ms).append(dt)

b_med = statistics.median(base_ms)
c_med = statistics.median(curr_ms)
print(json.dumps({"base_ms": b_med, "curr_ms": c_med, "speedup": b_med / c_med, "rows": len(curr_out)}))
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe, str(repo), str(workload_path)],
        input=base_src,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        err = (proc.stderr.strip() or proc.stdout.strip())[:240]
        return False, f"parity/speedup probe failed: {err}"
    info = json.loads(proc.stdout.strip())
    speedup = float(info["speedup"])
    ok = speedup >= 2.0
    return ok, (
        f"exact parity ({info['rows']} events); baseline={info['base_ms']:.2f}ms -> "
        f"current={info['curr_ms']:.2f}ms ({speedup:.1f}x speedup, need >= 2.0x)"
    )


def _break_pipeline(src: str) -> str:
    return (
        src
        + "\n\ndef process_events(raw_lines):\n"
        + "    return []\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    workload = ws / "program" / "workload.txt"
    log_path = ws / "program" / "clamber_log.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not workload.is_file():
        checks.append(("workspace-intact", False, "missing ./repo or program/workload.txt"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    base_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/pipeline.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    raw_log = ""
    if log_path.is_file():
        raw_log = log_path.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = json.loads(raw_log)
        except json.JSONDecodeError as exc:
            checks.append(("clamber-log-valid", False, f"invalid JSON: {exc}"))
        else:
            ok_log, log_detail = _validate_clamber_log(parsed)
            checks.append(("clamber-log-valid", ok_log, log_detail))
    else:
        checks.append(("clamber-log-valid", False, "missing program/clamber_log.json"))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    perf_ok, perf_detail = _verify_parity_and_speedup(repo, base_src, workload)
    checks.append(("parity-and-relative-speedup", perf_ok, perf_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/pipeline.py", _break_pipeline)
    checks.append(("mutation-caught", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text, raw_log]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

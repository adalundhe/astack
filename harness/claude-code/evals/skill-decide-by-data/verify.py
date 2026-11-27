#!/usr/bin/env python3
"""Executable verifier for `skill-decide-by-data`."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _extract_algo_ms(data: dict[str, Any], name: str) -> float | None:
    section = data.get(name)
    if isinstance(section, dict):
        for key in ("median_ms", "p50_ms", "mean_ms"):
            val = section.get(key)
            if isinstance(val, (int, float)) and not isinstance(val, bool) and float(val) > 0:
                return float(val)
    for flat in (f"{name}_median_ms", f"{name}_ms", f"{name}_mean_ms"):
        val = data.get(flat)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and float(val) > 0:
            return float(val)
    timings = data.get("timings") or data.get("results") or {}
    if isinstance(timings, dict):
        sub = timings.get(name)
        if isinstance(sub, dict):
            for key in ("median_ms", "p50_ms", "mean_ms"):
                val = sub.get(key)
                if isinstance(val, (int, float)) and not isinstance(val, bool) and float(val) > 0:
                    return float(val)
        elif isinstance(sub, (int, float)) and not isinstance(sub, bool) and float(sub) > 0:
            return float(sub)
    return None


def _ground_truth_dataset_check(repo: Path, dataset_path: Path) -> tuple[bool, int, str, float, float]:
    probe = r'''
import hashlib, json, statistics, sys, time
from pathlib import Path

repo = Path(sys.argv[1])
ds = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.path.insert(0, str(repo / "src"))
import algo_a, algo_b

orders = ds["orders"]
active = ds["active_ids"]
out_a = algo_a.find_matching_orders(orders, active)
out_b = algo_b.find_matching_orders(orders, active)
assert out_a == out_b, "ground-truth parity mismatch"

a_ms, b_ms = [], []
for i in range(3):
    t0 = time.perf_counter()
    algo_a.find_matching_orders(orders, active)
    a_ms.append((time.perf_counter() - t0) * 1000.0)
    t1 = time.perf_counter()
    algo_b.find_matching_orders(orders, active)
    b_ms.append((time.perf_counter() - t1) * 1000.0)

digest = hashlib.sha256(json.dumps(out_b, separators=(",", ":")).encode("utf-8")).hexdigest()
print(json.dumps({
    "count": len(out_b),
    "sha256": digest,
    "a_med": statistics.median(a_ms),
    "b_med": statistics.median(b_ms),
}))
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe, str(repo), str(dataset_path)],
        capture_output=True,
        text=True,
        timeout=25,
    )
    if proc.returncode != 0:
        return False, 0, "", 0.0, 0.0
    info = json.loads(proc.stdout.strip())
    return True, int(info["count"]), str(info["sha256"]), float(info["a_med"]), float(info["b_med"])


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    dataset = ws / "program" / "dataset.json"
    decision_path = ws / "program" / "decision.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not dataset.is_file():
        checks.append(("workspace-intact", False, "missing ./repo or program/dataset.json"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", clean_ok, clean_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("repo-unittest", ut_ok, ut_detail))

    checks.append(("decision-json-exists", decision_path.is_file(), str(decision_path.name)))

    raw_text = ""
    if not decision_path.is_file():
        checks.append(("decision-valid", False, "missing program/decision.json"))
        return _eval_kit.report_and_exit(checks)

    raw_text = decision_path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        checks.append(("decision-valid", False, f"invalid JSON: {exc}"))
        return _eval_kit.report_and_exit(checks)

    if not isinstance(data, dict):
        checks.append(("decision-valid", False, "decision.json must be a JSON object"))
        return _eval_kit.report_and_exit(checks)

    winner = data.get("winner")
    checks.append(("empirical-winner-algo-b", winner == "algo_b", f"winner={winner!r}"))

    parity = data.get("parity_verified")
    checks.append(("parity-verified", parity is True, f"parity_verified={parity!r}"))

    a_ms = _extract_algo_ms(data, "algo_a")
    b_ms = _extract_algo_ms(data, "algo_b")
    timings_ok = (
        a_ms is not None
        and b_ms is not None
        and a_ms > 0
        and b_ms > 0
        and (a_ms / b_ms) > 2.0
    )
    checks.append((
        "measured-timings-show-algo-b-faster",
        timings_ok,
        f"algo_a={a_ms}ms, algo_b={b_ms}ms" + (f", ratio={a_ms / b_ms:.1f}x" if a_ms and b_ms else ""),
    ))

    gt_ok, gt_count, gt_sha, gt_a, gt_b = _ground_truth_dataset_check(repo, dataset)
    count_ok = True
    if "output_count" in data:
        count_ok = data["output_count"] == gt_count
    sha_ok = True
    if "output_sha256" in data:
        sha_ok = data["output_sha256"] == gt_sha
    checks.append((
        "ground-truth-parity-and-speedup",
        gt_ok and count_ok and sha_ok and (gt_a > gt_b * 5.0),
        f"gt_count={gt_count} (match={count_ok}), sha_match={sha_ok}, "
        f"host_ratio={gt_a / gt_b:.1f}x" if gt_b > 0 else "ground truth failed",
    ))

    texts = [final_text, raw_text]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())

"""Separated offline oracle for `skill-decide-by-data`."""
from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Measure algo_a and algo_b on program/dataset.json and write program/decision.json."""
    script = r'''
import hashlib, json, statistics, sys, time
from pathlib import Path

ws = Path(sys.argv[1])
ds = json.loads((ws / "program" / "dataset.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ws / "repo" / "src"))
import algo_a, algo_b

orders = ds["orders"]
active_ids = ds["active_ids"]

# Warmup
for _ in range(2):
    assert algo_a.find_matching_orders(orders, active_ids) == algo_b.find_matching_orders(orders, active_ids)

a_ms, b_ms = [], []
out_ref = None
trials = 7
for idx in range(trials):
    order = ("a", "b") if idx % 2 == 0 else ("b", "a")
    outs = {}
    for side in order:
        fn = algo_a.find_matching_orders if side == "a" else algo_b.find_matching_orders
        t0 = time.perf_counter()
        res = fn(orders, active_ids)
        dt = (time.perf_counter() - t0) * 1000.0
        outs[side] = res
        (a_ms if side == "a" else b_ms).append(dt)
    assert outs["a"] == outs["b"], "parity mismatch"
    if out_ref is None:
        out_ref = outs["b"]

a_med = statistics.median(a_ms)
b_med = statistics.median(b_ms)
ratio = a_med / b_med
digest = hashlib.sha256(json.dumps(out_ref, separators=(",", ":")).encode("utf-8")).hexdigest()

decision = {
    "winner": "algo_b" if b_med < a_med else "algo_a",
    "parity_verified": True,
    "output_count": len(out_ref),
    "output_sha256": digest,
    "warmup_runs": 2,
    "trials": trials,
    "algo_a": {
        "median_ms": round(a_med, 4),
        "mean_ms": round(statistics.fmean(a_ms), 4),
        "stdev_ms": round(statistics.stdev(a_ms), 4),
        "trials": trials,
    },
    "algo_b": {
        "median_ms": round(b_med, 4),
        "mean_ms": round(statistics.fmean(b_ms), 4),
        "stdev_ms": round(statistics.stdev(b_ms), 4),
        "trials": trials,
    },
    "speedup_ratio": round(ratio, 2),
    "decided": f"algo_b wins on program/dataset.json ({b_med:.3f}ms vs {a_med:.3f}ms median, {ratio:.1f}x faster) with identical output ({len(out_ref)} matched orders, sha256={digest[:12]}).",
}
(ws / "program" / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
print(decision["decided"])
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", script, str(ws)],
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "final_text": (
            f"decided: {proc.stdout.strip()}\n"
            "Recorded empirical results in `program/decision.json` and left `./repo` unmodified."
        ),
    }

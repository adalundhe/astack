"""Separated offline oracle for `skill-benchmarking`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_BENCH_SCRIPT = '''#!/usr/bin/env python3
"""Reproducible statistical baseline benchmark for repo/src/aggregate.py."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "repo" / "src"))
from aggregate import aggregate_transactions, generate_records


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    pos = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _checksum(result: dict[str, dict[str, int]]) -> str:
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    dataset_size = 5000
    seed = 42
    warmup_runs = 3
    trials = 10

    records = generate_records(dataset_size, seed=seed)

    expected_checksum: str | None = None
    for _ in range(warmup_runs):
        out = aggregate_transactions(records)
        digest = _checksum(out)
        if expected_checksum is None:
            expected_checksum = digest
        elif digest != expected_checksum:
            raise RuntimeError("non-deterministic output during warmup")

    trials_ms: list[float] = []
    for _ in range(trials):
        t0 = time.perf_counter()
        out = aggregate_transactions(records)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        digest = _checksum(out)
        if digest != expected_checksum:
            raise RuntimeError("output checksum mismatch across trials")
        trials_ms.append(round(elapsed_ms, 4))

    ordered = sorted(trials_ms)
    report = {
        "benchmark": "aggregate_transactions",
        "dataset_size": dataset_size,
        "seed": seed,
        "warmup_runs": warmup_runs,
        "trials": trials,
        "trials_ms": trials_ms,
        "median_ms": round(statistics.median(ordered), 4),
        "p95_ms": round(_percentile(ordered, 95.0), 4),
        "mean_ms": round(statistics.fmean(ordered), 4),
        "stdev_ms": round(statistics.stdev(ordered), 4),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "output_checksum": expected_checksum,
        "platform": {
            "python_version": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "rerun_command": "python3 -B program/bench.py",
    }

    out_path = WS / "program" / "bench_results.json"
    out_path.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def apply(ws: Path) -> dict[str, object]:
    """Write program/bench.py and run it to create program/bench_results.json."""
    bench_py = ws / "program" / "bench.py"
    bench_py.write_text(_BENCH_SCRIPT, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-B", str(bench_py)],
        cwd=ws,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "final_text": (
            "Created reproducible baseline benchmark `program/bench.py` and saved results to "
            "`program/bench_results.json` without modifying `./repo`.\n"
            f"Rerun command: `python3 -B program/bench.py`\n{proc.stdout.strip()}"
        ),
    }

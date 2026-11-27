"""Separated offline oracle for `skill-baseline`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_BASELINE_BENCH = '''#!/usr/bin/env python3
"""Fair alternating same-input comparison of candidate vs competitor."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "repo" / "src"))
import candidate
import competitor


def _build_dataset(num_lines: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    vocab = [
        "Order", "event", "payment", "invoice", "ledger",
        "settlement", "audit", "retry", "queue", "worker",
        "timeout", "commit", "batch", "shard", "cursor",
    ]
    return [" ".join(rng.choices(vocab, k=12)) for _ in range(num_lines)]


def _percentile(sorted_vals: list[float], pct: float) -> float:
    pos = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _summarize(samples: list[float], dataset_lines: int, warmup_runs: int) -> dict[str, object]:
    ordered = sorted(samples)
    return {
        "dataset_lines": dataset_lines,
        "warmup_runs": warmup_runs,
        "trials": len(samples),
        "trials_ms": [round(x, 4) for x in samples],
        "median_ms": round(statistics.median(ordered), 4),
        "mean_ms": round(statistics.fmean(ordered), 4),
        "p95_ms": round(_percentile(ordered, 95.0), 4),
        "stdev_ms": round(statistics.stdev(ordered), 4),
    }


def main() -> int:
    dataset_lines = 2000
    seed = 2026
    warmup_runs = 3
    trials = 10

    lines = _build_dataset(dataset_lines, seed)
    out_path = WS / "program" / "baseline_report.json"

    for _ in range(warmup_runs):
        a = candidate.compute_word_freq(lines)
        b = competitor.compute_word_freq(lines)
        if a != b:
            out_path.write_text(json.dumps({"parity_verified": False}, indent=2) + "\\n", encoding="utf-8")
            print("ERROR: output parity mismatch during warmup", file=sys.stderr)
            return 1

    cand_ms: list[float] = []
    comp_ms: list[float] = []
    expected_out: dict[str, int] | None = None

    for round_idx in range(trials):
        order = ("candidate", "competitor") if round_idx % 2 == 0 else ("competitor", "candidate")
        round_outputs: dict[str, dict[str, int]] = {}
        for side in order:
            fn = candidate.compute_word_freq if side == "candidate" else competitor.compute_word_freq
            t0 = time.perf_counter()
            res = fn(lines)
            elapsed = (time.perf_counter() - t0) * 1000.0
            round_outputs[side] = res
            if side == "candidate":
                cand_ms.append(elapsed)
            else:
                comp_ms.append(elapsed)
        if round_outputs["candidate"] != round_outputs["competitor"]:
            out_path.write_text(json.dumps({"parity_verified": False}, indent=2) + "\\n", encoding="utf-8")
            print(f"ERROR: output parity mismatch on round {round_idx}", file=sys.stderr)
            return 1
        if expected_out is None:
            expected_out = round_outputs["candidate"]
        elif round_outputs["candidate"] != expected_out:
            print(f"ERROR: non-deterministic output on round {round_idx}", file=sys.stderr)
            return 1

    checksum = hashlib.sha256(
        json.dumps(expected_out, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    report = {
        "parity_verified": True,
        "output_checksum": checksum,
        "dataset_lines": dataset_lines,
        "seed": seed,
        "warmup_runs": warmup_runs,
        "trials": trials,
        "candidate": _summarize(cand_ms, dataset_lines, warmup_runs),
        "competitor": _summarize(comp_ms, dataset_lines, warmup_runs),
        "rigged_flaws": [
            "competitor received 10x larger input (10000 lines vs 1000 lines)",
            "competitor received zero warmup while candidate received 3 warmup passes",
            "single-shot timing with no alternating rounds or spread statistics",
            "no output parity verification between implementations",
        ],
        "platform": {
            "python_version": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "rerun_command": "python3 -B program/baseline_bench.py",
    }

    out_path.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def apply(ws: Path) -> dict[str, object]:
    """Write fair program/baseline_bench.py and run it to create program/baseline_report.json."""
    bench_py = ws / "program" / "baseline_bench.py"
    bench_py.write_text(_BASELINE_BENCH, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-B", str(bench_py)],
        cwd=ws,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "final_text": (
            "Audited `program/rigged_bench.py` (10x input mismatch, missing warmup on competitor, single-shot timing, "
            "no output parity check). Left `./repo` unmodified, wrote fair alternating comparison script "
            "`program/baseline_bench.py`, and recorded parity-verified metrics in `program/baseline_report.json`.\n"
            f"Rerun command: `python3 -B program/baseline_bench.py`\n{proc.stdout.strip()}"
        ),
    }

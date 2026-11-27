"""Separated offline oracle for `skill-clamber`."""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

_STEP1_SRC = '''"""Log event parsing and deduplication pipeline."""
from __future__ import annotations

import re
from typing import Any


def process_events(raw_lines: list[str]) -> list[dict[str, Any]]:
    """Parse structured event lines, drop malformed lines, and deduplicate by req ID keeping first seen."""
    results: list[dict[str, Any]] = []
    seen_req_ids: set[str] = set()

    for line in raw_lines:
        ts_match = re.compile(r"^(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z)\\s+").search(line)
        if not ts_match:
            continue

        fields: dict[str, str] = {}
        valid = True
        for key in ("level", "req", "user", "latency_ms", "status"):
            pat = re.compile(rf"\\b{key}=([^\\s]+)")
            m = pat.search(line)
            if not m:
                valid = False
                break
            fields[key] = m.group(1)
        if not valid:
            continue

        req_id = fields["req"]
        if req_id in seen_req_ids:
            continue
        seen_req_ids.add(req_id)

        results.append(
            {
                "ts": ts_match.group(1),
                "level": fields["level"],
                "req": req_id,
                "user": fields["user"],
                "latency_ms": int(fields["latency_ms"]),
                "status": int(fields["status"]),
            }
        )
    return results
'''

_STEP2_SRC = '''"""Log event parsing and deduplication pipeline."""
from __future__ import annotations

import re
from typing import Any

_TS_RE = re.compile(r"^(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z)\\s+")
_KV_RE = re.compile(r"\\b(level|req|user|latency_ms|status)=([^\\s]+)")
_REQUIRED_KEYS = frozenset({"level", "req", "user", "latency_ms", "status"})


def process_events(raw_lines: list[str]) -> list[dict[str, Any]]:
    """Parse structured event lines, drop malformed lines, and deduplicate by req ID keeping first seen."""
    results: list[dict[str, Any]] = []
    seen_req_ids: set[str] = set()
    ts_match_fn = _TS_RE.match
    kv_findall = _KV_RE.findall

    for line in raw_lines:
        ts_match = ts_match_fn(line)
        if ts_match is None:
            continue

        fields: dict[str, str] = {}
        for key, value in kv_findall(line):
            if key not in fields:
                fields[key] = value
        if len(fields) < 5 or not _REQUIRED_KEYS.issubset(fields):
            continue

        req_id = fields["req"]
        if req_id in seen_req_ids:
            continue
        seen_req_ids.add(req_id)

        results.append(
            {
                "ts": ts_match.group(1),
                "level": fields["level"],
                "req": req_id,
                "user": fields["user"],
                "latency_ms": int(fields["latency_ms"]),
                "status": int(fields["status"]),
            }
        )
    return results
'''


def _measure(ws: Path) -> dict[str, object]:
    probe = r'''
import hashlib, json, statistics, sys, time
from pathlib import Path

ws = Path(sys.argv[1])
lines = (ws / "program" / "workload.txt").read_text(encoding="utf-8").splitlines()
sys.path.insert(0, str(ws / "repo" / "src"))
import pipeline

out = pipeline.process_events(lines)
for _ in range(2):
    pipeline.process_events(lines)

samples = []
for _ in range(7):
    t0 = time.perf_counter()
    res = pipeline.process_events(lines)
    samples.append((time.perf_counter() - t0) * 1000.0)
    assert res == out

digest = hashlib.sha256(json.dumps(out, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
print(json.dumps({
    "median_ms": round(statistics.median(samples), 4),
    "mean_ms": round(statistics.fmean(samples), 4),
    "stdev_ms": round(statistics.stdev(samples), 4),
    "trials": len(samples),
    "output_count": len(out),
    "output_sha256": digest,
}))
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe, str(ws)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip())


def _run_tests(repo: Path) -> bool:
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def apply(ws: Path) -> dict[str, object]:
    """Run two isolated hill-climbing steps on repo/src/pipeline.py and save program/clamber_log.json."""
    repo = ws / "repo"
    pipe_file = repo / "src" / "pipeline.py"

    base = _measure(ws)
    ref_sha = base["output_sha256"]

    # Step 1: O(n^2) list dedup -> O(1) set lookup
    pipe_file.write_text(_STEP1_SRC, encoding="utf-8")
    tests1 = _run_tests(repo)
    m1 = _measure(ws)
    assert tests1 and m1["output_sha256"] == ref_sha

    # Step 2: Hoist regex compilation out of inner loop into precompiled module patterns
    pipe_file.write_text(_STEP2_SRC, encoding="utf-8")
    tests2 = _run_tests(repo)
    m2 = _measure(ws)
    assert tests2 and m2["output_sha256"] == ref_sha

    log = {
        "workload": "program/workload.txt",
        "baseline": base,
        "steps": [
            {
                "step": 1,
                "hypothesis": "Replacing O(n^2) list membership checks for seen_req_ids with a set removes quadratic scan time.",
                "change": "Changed seen_req_ids from list[str] to set[str] in src/pipeline.py.",
                "before_median_ms": base["median_ms"],
                "after_median_ms": m1["median_ms"],
                "after_stdev_ms": m1["stdev_ms"],
                "parity_verified": m1["output_sha256"] == ref_sha,
                "tests_passed": tests1,
                "outcome": "kept",
            },
            {
                "step": 2,
                "hypothesis": "Hoisting regex compilation to module level avoids 6 re.compile calls per input line.",
                "change": "Replaced inner-loop re.compile calls with precompiled _TS_RE and _KV_RE patterns.",
                "before_median_ms": m1["median_ms"],
                "after_median_ms": m2["median_ms"],
                "after_stdev_ms": m2["stdev_ms"],
                "parity_verified": m2["output_sha256"] == ref_sha,
                "tests_passed": tests2,
                "outcome": "kept",
            },
        ],
    }
    (ws / "program" / "clamber_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return {
        "final_text": (
            f"Optimized `./repo/src/pipeline.py` in two isolated measured steps: "
            f"baseline {base['median_ms']}ms -> step 1 (set dedup) {m1['median_ms']}ms -> "
            f"step 2 (hoisted regexes) {m2['median_ms']}ms with verified output parity and passing unit tests. "
            "Experiment log saved to `program/clamber_log.json`."
        ),
    }

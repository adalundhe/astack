#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/pipeline.py <<'EOF'
"""Log event parsing and deduplication pipeline."""
from __future__ import annotations

import re
from typing import Any


def process_events(raw_lines: list[str]) -> list[dict[str, Any]]:
    """Parse structured event lines, drop malformed lines, and deduplicate by req ID keeping first seen."""
    results: list[dict[str, Any]] = []
    seen_req_ids: list[str] = []

    for line in raw_lines:
        ts_match = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+").search(line)
        if not ts_match:
            continue

        fields: dict[str, str] = {}
        valid = True
        for key in ("level", "req", "user", "latency_ms", "status"):
            pat = re.compile(rf"\b{key}=([^\s]+)")
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
        seen_req_ids.append(req_id)

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
EOF

cat > repo/tests/test_pipeline.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import process_events


class PipelineTest(unittest.TestCase):
    def test_parses_valid_lines_and_skips_malformed(self):
        lines = [
            "2026-11-26T10:00:01Z level=INFO req=r1 user=u1 latency_ms=12 status=200",
            "garbage line without timestamp",
            "2026-11-26T10:00:02Z level=WARN req=r2 user=u2 latency_ms=45",
            "2026-11-26T10:00:03Z level=ERROR req=r3 user=u3 latency_ms=90 status=500",
        ]
        got = process_events(lines)
        self.assertEqual(
            got,
            [
                {"ts": "2026-11-26T10:00:01Z", "level": "INFO", "req": "r1", "user": "u1", "latency_ms": 12, "status": 200},
                {"ts": "2026-11-26T10:00:03Z", "level": "ERROR", "req": "r3", "user": "u3", "latency_ms": 90, "status": 500},
            ],
        )

    def test_deduplicates_by_req_keeping_first_occurrence(self):
        lines = [
            "2026-11-26T10:00:01Z level=INFO req=dup1 user=u1 latency_ms=10 status=200",
            "2026-11-26T10:00:02Z level=WARN req=dup1 user=u2 latency_ms=99 status=503",
            "2026-11-26T10:00:03Z level=INFO req=ok2 user=u3 latency_ms=15 status=201",
        ]
        got = process_events(lines)
        self.assertEqual([row["req"] for row in got], ["dup1", "ok2"])
        self.assertEqual(got[0]["user"], "u1")
        self.assertEqual(got[0]["latency_ms"], 10)
EOF

python3 -B - <<'EOF'
import random
from pathlib import Path

rng = random.Random(2026)
levels = ["INFO", "WARN", "ERROR"]
statuses = [200, 201, 204, 400, 404, 500, 503]
lines: list[str] = []
seen_pool: list[str] = []

for i in range(2500):
    if i % 25 == 0:
        lines.append(f"malformed entry #{i} missing structured fields")
        continue
    if seen_pool and i % 5 == 0:
        req_id = rng.choice(seen_pool)
    else:
        req_id = f"req-{i:06d}"
        seen_pool.append(req_id)
    sec = i % 60
    minute = (i // 60) % 60
    lines.append(
        f"2026-11-26T10:{minute:02d}:{sec:02d}Z "
        f"level={rng.choice(levels)} req={req_id} user=u{rng.randint(1, 200)} "
        f"latency_ms={rng.randint(1, 500)} status={rng.choice(statuses)}"
    )

Path("program/workload.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
EOF

cat > program/clamber_brief.md <<'EOF'
# Performance Hill-Climb Brief: Event Pipeline

`./repo/src/pipeline.py:process_events` is too slow on `program/workload.txt`.

Requirements:
1. Measure a baseline on `program/workload.txt` (warmup + multi-trial median and stdev) while keeping all unit tests passing.
2. Identify the bottlenecks and eliminate them one isolated step at a time (at least 2 distinct incremental steps). After each step:
   - Run unit tests and confirm exact output parity with the baseline output.
   - Re-measure median and stdev on `program/workload.txt`.
   - Keep the change if it measurably improves performance; revert otherwise.
3. Save the full experiment log to `program/clamber_log.json` with:
   - `baseline`: object with `median_ms`, `stdev_ms`, `trials`, and `output_count`
   - `steps`: list of >= 2 step objects, each with `step`, `hypothesis`, `change`, `before_median_ms`, `after_median_ms`, `after_stdev_ms`, `parity_verified: true`, `tests_passed: true`, and `outcome` (`"kept"` or `"reverted"`)
4. Leave `./repo/src/pipeline.py` updated with the winning optimizations and unit tests green.
EOF

git -C repo add .
git -C repo commit -q -m "initial event pipeline"

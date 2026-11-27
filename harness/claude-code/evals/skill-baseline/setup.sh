#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/candidate.py <<'EOF'
"""Candidate word frequency implementation."""
from __future__ import annotations


def compute_word_freq(lines: list[str]) -> dict[str, int]:
    """Count lowercase whitespace-delimited words across all lines."""
    counts: dict[str, int] = {}
    for line in lines:
        for word in line.lower().split():
            if word in counts:
                counts[word] = counts[word] + 1
            else:
                counts[word] = 1
    return counts
EOF

cat > repo/src/competitor.py <<'EOF'
"""Competitor word frequency implementation."""
from __future__ import annotations

from collections import Counter


def compute_word_freq(lines: list[str]) -> dict[str, int]:
    """Count lowercase whitespace-delimited words across all lines."""
    counter: Counter[str] = Counter()
    for line in lines:
        counter.update(line.lower().split())
    return dict(counter)
EOF

cat > repo/tests/test_freq.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import candidate
import competitor


class WordFreqTest(unittest.TestCase):
    def test_both_implementations_match(self):
        lines = ["Alpha beta alpha", "BETA gamma", "alpha"]
        expected = {"alpha": 3, "beta": 2, "gamma": 1}
        self.assertEqual(candidate.compute_word_freq(lines), expected)
        self.assertEqual(competitor.compute_word_freq(lines), expected)
EOF

cat > program/rigged_bench.py <<'EOF'
#!/usr/bin/env python3
"""Biased benchmark submitted by teammate (do not trust!)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "repo" / "src"))
import candidate
import competitor

base_line = "Order event payment invoice ledger settlement audit retry queue worker "

# Candidate gets 1,000 lines and 3 warmup passes
cand_input = [base_line] * 1000
for _ in range(3):
    candidate.compute_word_freq(cand_input)
t0 = time.perf_counter()
candidate.compute_word_freq(cand_input)
cand_ms = (time.perf_counter() - t0) * 1000.0

# Competitor gets 10,000 lines (10x larger!) and zero warmup
comp_input = [base_line] * 10000
t1 = time.perf_counter()
competitor.compute_word_freq(comp_input)
comp_ms = (time.perf_counter() - t1) * 1000.0

print(f"candidate={cand_ms:.2f}ms competitor={comp_ms:.2f}ms ratio={comp_ms / cand_ms:.1f}x")
EOF

cat > program/baseline_ask.md <<'EOF'
# Fair Baseline Comparison Request

Audit `program/rigged_bench.py` and replace its flawed comparison with a fair, reproducible benchmark.

Requirements:
- Leave `./repo` unmodified.
- Write a runnable stdlib script `program/baseline_bench.py` that compares `candidate.compute_word_freq` and `competitor.compute_word_freq` on:
  - the **exact same deterministic input dataset** (at least 1,000 lines, seeded),
  - **identical warmup runs** (`>= 2`) for both sides before timing,
  - **alternating measured rounds** (`>= 5` trials per side, e.g. 10 rounds alternating execution order),
  - **strict output parity verification** on every trial (fail non-zero and mark `parity_verified: false` if outputs differ).
- Running `python3 -B program/baseline_bench.py` offline must write `program/baseline_report.json` containing:
  - `parity_verified`: `true`
  - `dataset_lines`: integer line count used identically for both sides
  - `warmup_runs`: integer warmup count applied equally to both sides
  - `trials`: integer trial count per side (`>= 5`)
  - `candidate`: `{ "dataset_lines": ..., "warmup_runs": ..., "trials": ..., "median_ms": ..., "mean_ms": ..., "p95_ms": ..., "stdev_ms": ... }`
  - `competitor`: `{ "dataset_lines": ..., "warmup_runs": ..., "trials": ..., "median_ms": ..., "mean_ms": ..., "p95_ms": ..., "stdev_ms": ... }`
  - `rigged_flaws`: list of methodological flaws found in `program/rigged_bench.py`
  - `platform`: environment metadata object
  - `rerun_command`: exact command to reproduce
EOF

git -C repo add .
git -C repo commit -q -m "initial candidate and competitor implementations"

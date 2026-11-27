---
type: llm
---

Evaluate the benchmark audit, fair comparison script, report, and repository state against `baseline`.

PASS if all of these hold:
- Identifies the methodological flaws in `program/rigged_bench.py` (10x larger input for competitor, zero warmup for competitor, single-shot timing, no output parity check).
- Leaves `./repo` unmodified (`git status` clean).
- Writes `program/baseline_bench.py` executing both implementations on identical seeded inputs with identical warmup, alternating measured rounds (>= 5 trials), and strict output parity checking.
- Saves `program/baseline_report.json` with `parity_verified: true`, identical input sizes, per-side statistical summaries, and platform metadata, and reports the fair comparison results and rerun command.

FAIL otherwise.

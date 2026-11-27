---
type: llm
---

Evaluate the benchmark script, saved results, repository state, and final report against `benchmarking`.

PASS if all of these hold:
- Leaves `./repo` unmodified (`git status` clean) because the task asked for a baseline measurement before optimizing.
- Writes a runnable Python stdlib benchmark script at `program/bench.py` with warmup iterations, >= 5 measured trials, deterministic dataset generation, and output verification proving real work executed.
- Saves `program/bench_results.json` with absolute timing statistics (`median_ms`, `p95_ms`, `mean_ms`, spread), exact dataset size, and platform metadata.
- Reports the measured baseline numbers, variance/spread, environment details, and exact rerun command in the final response.

FAIL otherwise.

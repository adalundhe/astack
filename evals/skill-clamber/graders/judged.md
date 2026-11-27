---
type: llm
---

Evaluate the hill-climbing log, optimized pipeline, tests, and final reply against `clamber`.

PASS if all of these hold:
- Establishes a baseline measurement on `program/workload.txt` before making changes.
- Eliminates both bottlenecks in `repo/src/pipeline.py` (O(n^2) list dedup scan and inner-loop regex compilation) in >= 2 isolated incremental steps, verifying unit tests and exact output parity after each step.
- Records baseline and every step (hypothesis, change, before/after median and spread, parity, tests, kept/reverted outcome) in `program/clamber_log.json`.
- Leaves `./repo/src/pipeline.py` measurably faster than root commit with tests passing and all gates intact.

FAIL otherwise.

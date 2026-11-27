---
type: llm
---

Evaluate the A/B benchmark results, grafted implementation, cleanup, and test suite against `ab-test`.

PASS if all of these hold:
- Prototypes and benchmarks at least two distinct prefix-matching implementations alongside the baseline on `program/queries.json` in alternating trials with parity checks.
- Records all variants, timings, parity verification, and winning choice in `program/ab_results.json`.
- Grafts only the verified faster winner into `./repo/src/matcher.py` and removes any losing variant code from `./repo`.
- Preserves exact output parity, passes unit tests, and keeps all gates intact.

FAIL otherwise.

---
description: "Benchmark baseline and >=2 candidate optimizations for repo/src/engine.py in program/ab_results.json, achieve >=5x speedup on program/workload.json with 100% exact Unicode and full-scan parity, and reject arbitrary scan-cap shortcuts."
expected_outcome: "Measures baseline and at least 2 candidate optimization variants in program/ab_results.json with parity verification, lands the winning optimization in repo/src/engine.py achieving >=5x relative speedup over root commit without truncating scans or dropping Unicode NFKC/casefold accuracy, adds accuracy regression tests catching both traps, and leaves no losing variant files in repo."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md` and optimize the event search and aggregation engine in `./repo/src/engine.py` against `program/workload.json`.

Measure the baseline and at least two candidate optimization approaches in `program/ab_results.json`, land only the winning implementation in `./repo/src/engine.py` achieving at least a 5x speedup over the original implementation with 100% exact output parity (including all Unicode normalization and full-dataset matches), and expand `./repo/tests/test_engine.py` so accuracy shortcuts fail the test suite.

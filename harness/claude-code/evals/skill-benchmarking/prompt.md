---
description: "Build a reproducible statistical benchmark for repo/src/aggregate.py before optimizing, leaving ./repo untouched."
expected_outcome: "Reads benchmarking/SKILL.md, leaves ./repo clean, writes runnable stdlib script program/bench.py with warmup and multi-trial statistics plus output verification, and saves results with dataset size and platform metadata to program/bench_results.json."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/bench_ask.md` and build the requested reproducible benchmark for `./repo/src/aggregate.py` before any optimization work begins.

Leave `./repo` unmodified, place the runnable benchmark script at `program/bench.py`, and save the measured multi-trial results in `program/bench_results.json`. Report the baseline metrics, spread, environment, and exact rerun command.

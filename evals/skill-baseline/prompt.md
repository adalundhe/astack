---
description: "Audit a rigged competitor benchmark and build a fair same-input, same-warmup, output-parity-verified comparison without modifying ./repo."
expected_outcome: "Reads baseline/SKILL.md, identifies the 10x input mismatch and missing warmup in program/rigged_bench.py, leaves ./repo clean, writes alternating fair comparison script program/baseline_bench.py with output parity verification, and saves program/baseline_report.json with parity_verified true."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` A teammate ran `program/rigged_bench.py` and claimed `./repo/src/candidate.py` is 10x faster than `./repo/src/competitor.py`. Read `program/baseline_ask.md` and `program/rigged_bench.py`, audit the comparison methodology, and build a fair comparison benchmark at `program/baseline_bench.py` with results saved in `program/baseline_report.json`.

Leave `./repo` unmodified. Report the flaws in the original benchmark, the fair comparison metrics with spread, parity proof, environment metadata, and exact rerun command.

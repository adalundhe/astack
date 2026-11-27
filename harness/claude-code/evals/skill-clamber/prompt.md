---
description: "Optimize repo/src/pipeline.py in isolated measured hill-climbing steps, recording baseline and >= 2 kept improvements with parity proof in program/clamber_log.json."
expected_outcome: "Reads clamber/SKILL.md, profiles and removes both bottlenecks in repo/src/pipeline.py in separate measured steps (O(n^2) dedup list scan and inner-loop regex compilation), logs baseline and >= 2 incremental steps with output parity in program/clamber_log.json, achieves measurable speedup over root commit, and passes unittest, mutation check, and gate check."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/clamber_brief.md` and optimize `./repo/src/pipeline.py` on `program/workload.txt` using isolated, measured step-by-step improvements.

Record the baseline measurement and each incremental step (hypothesis, change, before/after median and spread, test status, output parity, kept/reverted outcome) in `program/clamber_log.json`. Keep `./repo/src/pipeline.py` updated with the verified faster implementation and confirm unit tests pass.

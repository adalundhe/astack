---
description: "Prototype >= 2 distinct shortest-path architectures in program/candidates/, benchmark them with parity in program/swarm_report.json, and land the winning design in repo/src/router.py."
expected_outcome: "Reads swarm-hypothesis/SKILL.md, prototypes >= 2 distinct candidate implementations in program/candidates/, benchmarks baseline and candidates with output parity in program/swarm_report.json, lands the winning faster architecture in repo/src/router.py, passes unittest and mutation check, and keeps gates intact."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/goal.md` and optimize `./repo/src/router.py` by prototyping at least two distinct algorithmic architectures in `program/candidates/`, measuring them against the baseline on `program/graph_workload.json` with exact output parity, and landing the winning implementation in `./repo/src/router.py`.

Record all candidates' measured timings, parity checks, and winning pick in `program/swarm_report.json`, keep `./repo` free of extra candidate files, and confirm unit tests pass.

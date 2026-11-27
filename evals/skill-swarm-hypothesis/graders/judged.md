---
type: llm
---

Evaluate the candidate prototypes, benchmark report, landed router implementation, and test results against `swarm-hypothesis`.

PASS if all of these hold:
- Prototypes >= 2 genuinely distinct shortest-path candidate architectures in `program/candidates/`.
- Benchmarks baseline and all candidates on `program/graph_workload.json` with exact output parity recorded in `program/swarm_report.json`.
- Lands only the winning implementation in `./repo/src/router.py`, leaving no extra candidate modules inside `./repo`.
- Achieves measurable speedup over root commit while passing unit tests and keeping all gates intact.

FAIL otherwise.

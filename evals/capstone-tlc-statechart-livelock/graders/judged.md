---
type: llm
---

Evaluate the job coordinator refactor, exhaustive state-space checker, counterexample traces, Mermaid statechart, and test suite.

PASS if all of these hold:
- Replaces the 4 overlapping booleans (`claiming`, `running`, `retrying`, `timed_out`) in `./repo/src/coordinator.py` with explicit `Enum` states (`QUEUED`, `CLAIMED`, `RUNNING`, `RETRY_WAIT`, `COMPLETED`, `DEAD_LETTER`) and centralized transitions.
- Writes an exhaustive BFS checker at `program/check_protocol.py` that catches both safety (dual ownership) and liveness (unbounded retry livelock) on the buggy root commit and finds 0 violations on the fixed code.
- Records buggy-model counterexample traces in `program/counterexample.json` and a faithful Mermaid `stateDiagram-v2` in `program/STATES.md`.
- Expands `./repo/tests/test_coordinator.py` so both safety and livelock regressions fail the test suite, while gates stay intact.

FAIL otherwise.

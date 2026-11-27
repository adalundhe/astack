---
description: "Replace overlapping boolean flags in repo/src/coordinator.py with explicit Enum states, build an exhaustive BFS state-space checker in program/check_protocol.py, capture buggy safety and livelock counterexamples in program/counterexample.json, document the Mermaid stateDiagram-v2 in program/STATES.md, and fix both bugs."
expected_outcome: "Replaces the 4 overlapping booleans in src/coordinator.py with explicit Enum states and centralized transitions, writes an exhaustive BFS model checker at program/check_protocol.py that catches the buggy root commit and reports 0 safety/liveness violations on the fixed code, records the buggy counterexamples in program/counterexample.json, writes a valid Mermaid stateDiagram-v2 in program/STATES.md, and passes unittest, two resilient mutations (safety + livelock), and gate checks."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md` and formally analyze and repair the job coordinator in `./repo/src/coordinator.py`.

Capture counterexample traces for the current protocol violations in `program/counterexample.json`, write a deterministic exhaustive BFS state-space checker at `program/check_protocol.py`, replace the overlapping boolean flags in `./repo/src/coordinator.py` with an explicit `Enum` state machine and centralized transition table, document the verified state machine in `program/STATES.md`, expand `./repo/tests/test_coordinator.py` across the state space and counterexample replays, and prove zero safety or liveness violations remain.

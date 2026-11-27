---
description: "Harden an upstream HTTP client and health endpoints with bounded timeouts, jittered retry budgets, and decoupled liveness vs readiness probes."
expected_outcome: "Reads fail-safely/SKILL.md, adds finite timeouts, bounded jittered exponential backoff with a retry budget for idempotent GETs only, decouples liveness from the DB probe, bounds readiness timeout, and proves resilience with injected-fault unit tests."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Harden the upstream HTTP client and health endpoints in `./repo` (`src/gateway.py`) so partial downstream failures cannot hang callers, trigger retry storms, or cause fleet restart loops.

Read `./repo/README.md` for the public API and requirements. Fix the defects in `./repo/src/gateway.py`, add unit tests under `./repo/tests/` proving behavior under injected timeouts, 5xx bursts, non-idempotent POST failures, and slow or failing DB probes, and verify all tests pass.

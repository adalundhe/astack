---
description: "Fix a job queue processor with exploding high-cardinality metric labels, silent failure drops without a DLQ, and missing correlation IDs in structured logs."
expected_outcome: "Reads observable-by-default/SKILL.md, switches metrics to bounded-cardinality labels (job_type, outcome, error_type), propagates trace_id in structured logs, tracks last_success_ts and dlq_depth, retries transient failures and routes unrecoverable jobs to the dead-letter queue, and adds behavior tests."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` The background job queue worker in `./repo` (`src/queue_worker.py`) is causing metrics-backend cardinality explosions, silently dropping failed jobs with no dead-letter queue, and emitting logs without correlation IDs.

Read `./repo/README.md` for the worker contract and telemetry requirements. Fix `./repo/src/queue_worker.py` to keep metric cardinality bounded, propagate trace/correlation IDs in structured logs, record worker heartbeat and DLQ depth, and route unrecoverable failures to the dead-letter queue after bounded retries. Add tests under `./repo/tests/` proving all of these behaviors, and verify all tests pass.

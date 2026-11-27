---
description: "Atomic outcome eval for triage: correlates incident timeline under program/incident/, persists a scrubbed timestamped capture under ASTACK_HOME/checkout/logging/logs/, isolates the rev-482 connection-pool leak in repo/src/pool.py while rejecting the disk alert decoy, and leaves ./repo clean."
expected_outcome: "Reads triage/SKILL.md, saves a scrubbed UTC-stamped diagnostic capture under program/astack_home/checkout/logging/logs/, correlates rev-482 deploy onset to p99 latency spike and pool exhaustion in repo/src/pool.py, disproves the 61% disk usage alert decoy, recommends reversible rollback to rev-481 plus permanent fix handoff in program/TRIAGE.md, and leaves ./repo clean."
timeout_seconds: 360
---

`/astack:go` Checkout API in project `checkout` is throwing elevated 503 errors and latency spikes in production. An incident bundle has been collected under `program/incident/` alongside the service repo in `./repo`. Using `program/astack_home` as `ASTACK_HOME`, triage the incident without modifying `./repo`: preserve a scrubbed diagnostic capture in the project's logging directory, correlate the timeline to isolate the proven root cause (ruling out any unrelated alerts), and write your triage dossier with a reversible mitigation and handoff plan to `program/TRIAGE.md`.

---
description: "Triage edge-api payment outage using program/incident/, save scrubbed UTC-stamped logs and traces under program/astack_home/edge-api/logging/, write program/INCIDENT_REPORT.md pinpointing subnet-pay-2 egress DROP and rejecting the CPU decoy, and harden repo/src/gateway.py."
expected_outcome: "Saves scrubbed UTC-stamped diagnostic logs and traces under program/astack_home/edge-api/logging/{logs,traces}/ with zero secret leaks, writes program/INCIDENT_REPORT.md isolating subnet-pay-2 TCP/443 egress DROP and the gateway retry storm while ruling out the CPU warning decoy, hardens repo/src/gateway.py with bounded timeout, jittered retry budget, header redaction, and bounded metric labels, and passes unittest, resilient mutations, secret sweeps, and gate checks."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md`, investigate the incident evidence under `program/incident/` for project `edge-api`, and harden `./repo/src/gateway.py`.

Persist scrubbed diagnostic log and network-trace captures under `program/astack_home/edge-api/logging/` (`logs/` and `traces/`), write your findings and root-cause analysis to `program/INCIDENT_REPORT.md`, fix the failure-amplification, secret-logging, and metric-cardinality defects in `./repo/src/gateway.py`, and expand `./repo/tests/test_gateway.py` to guard against regressions.

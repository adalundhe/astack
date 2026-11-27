---
type: llm
---

Evaluate the incident triage, network trace isolation, scrubbed log persistence, and payment gateway hardening.

PASS if all of these hold:
- Saves scrubbed UTC-stamped diagnostic captures under `program/astack_home/edge-api/logging/logs/` and `traces/` with zero leaked bearer token (`sk-prod-incident98765432`).
- Writes `program/INCIDENT_REPORT.md` accurately pinpointing the `subnet-pay-2` TCP/443 egress `DROP` (`sg-pay-2`/`nacl-pay-2`/`fw-change-882`) and gateway retry storm, clearing DNS/TLS/subnet-pay-1, and ruling out the unrelated CPU warning decoy.
- Hardens `./repo/src/gateway.py` with a finite positive timeout, bounded backoff+jitter retry budget, redacted auth header logging, and low-cardinality metric labels (no `request_id` label).
- Expands `./repo/tests/test_gateway.py` so retry-storm, secret-logging, and high-cardinality mutations are all caught while gates remain intact.

FAIL otherwise.

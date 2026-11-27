---
type: llm
---

Evaluate the network trace against `net-trace/SKILL.md`.

PASS if all of these hold:
- Saves a UTC-stamped trace capture under `program/astack_home/edge-gw/logging/traces/` containing the `subnet-app-2` egress TCP/443 `DROP` flow-log verdicts with zero secrets.
- Traces hop-by-hop from DNS -> routing -> flow logs & bidirectional SG/NACL policies -> TLS, clearing DNS (`api.partner.internal` CNAME -> `198.51.100.44`), routes (`nat-gw-01`), TLS cert chain (valid until `2027-06-01`), and the healthy `subnet-app-1` decoy.
- Pinpoints the exact failing hop: outbound TCP/443 from `subnet-app-2` is dropped (`action=DROP reason=NO_MATCHING_EGRESS_RULE`) because both `sg-app-2` and `nacl-app-2` lack an outbound TCP/443 rule to `198.51.100.44/32` (while inbound ephemeral return rule 100 on `nacl-app-2` already exists).
- Recommends a minimal least-privilege fix scoped to TCP/443 -> `198.51.100.44/32` on `sg-app-2` and `nacl-app-2` without modifying `./repo`.

FAIL otherwise.

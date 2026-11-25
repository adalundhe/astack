---
name: triage
description: "Structured live-infrastructure and multi-layer systems debugging across any cloud, edge/CDN, orchestrator, serverless, or host platform: confirm target context, preserve volatile evidence before restarts, correlate recent deploys/IaC/audit logs, isolate across layers with safe read-only probes, separate reversible mitigation from root cause, and hand confirmed code/IaC bugs to bugbash."
---

# Triage

Isolate live infrastructure and distributed-systems failures across cloud, edge, cluster, and host layers without destroying evidence or worsening the outage. Stabilize safely first, then prove root cause and hand off permanent fixes.

Hand confirmed code or IaC bugs to **bugbash** once isolated. Discover whichever provider CLIs, APIs, and observability systems apply via **analyze-environment**—never assume a fixed vendor list.

## 1. Lock context and preserve volatile evidence first

1. **Verify target environment (**analyze-environment**):** confirm exact account, project/zone, region, cluster/namespace, and IaC workspace in `TOOLS.md` before running any command. Never mutate production without explicit human approval (**decisions-in-plain-words**).
2. **Capture volatile state before restarting or draining anything,** because restarts erase crash evidence: grab current and previous logs, platform events, stack/thread dumps, open FDs/sockets, conntrack/DNS/metrics snapshots, and error traces. Save artifacts as `<file>_DEBUG_<shorthash>.<type>` with zero secrets (**no-leaked-secrets**).
3. **Pin down symptom and blast radius:** what is failing, for which tenants/regions/edge PoPs/services, since what exact UTC time, and at what error rate or latency?

## 2. Correlate recent changes before deep-diving

Inspect every change near onset with safe read-only probes:

- app, container, serverless, or edge deploys, GitOps syncs, and feature-flag flips;
- IaC applies, IAM/security merges, DNS/CDN/WAF/routing edits, and secret or TLS rotations;
- platform audit logs, autoscaling events, and upstream provider status or quota changes.

## 3. Isolate systematically across layers (read-only probes)

Dispatch read-only `astack-researcher` or `astack-reviewer` probes in parallel across suspect layers (under **lead**'s clocks) to bisect where requests break:

- **Edge, CDN, WAF, DNS, TLS, & network (**net-trace**):** WAF/bot/rate-limit/SSL mode, LB/ingress health, DNS/DNSSEC, cert chain/SNI/mTLS, firewall/network policies, flow logs, packet captures, NAT/conntrack limits.
- **Compute & orchestrator:** OOMs, evictions, cold starts, subrequest/CPU/disk/inode/IOPS limits, CNI networking, stuck sync hooks.
- **Process & runtime:** thread, goroutine, or connection-pool exhaustion, FD limits, GC pauses, deadlocks, retry storms (**fail-safely**).
- **Data, identity, & control planes:** DB locks, slow queries, WAL/vacuum bloat, queue/DLQ lag, cache stampedes, IAM/RBAC/token denials (**least-privilege**), provider quota cliffs.

Cite the exact command and observed output for every claim (ran vs. read)—never guess the failing layer.

## 4. Separate safe mitigation from permanent fix

1. **Propose reversible mitigation first (**decisions-in-plain-words**):** if service is degraded, present the safest reversible action (rollback, traffic drain, failover, WAF bypass, scale up, flag off) with its blast radius, check, and rollback path, honoring `autonomy`.
2. **Hand off root causes cleanly:**
   - Code, migration, or IaC defect -> **bugbash** with the triage dossier (**safe-to-deploy**, **safe-iac**, **least-privilege**, **fail-safely**).
   - Missing telemetry or runbook gap -> **observable-by-default** and **technical-writing**.
   - Record the timeline, disproved hypotheses (`decided:`), and structural guards via **lookback** + **make-it-stick**, then remove temp captures (**cleanup**).

Referenced skills: `bugbash` (`../bugbash/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `net-trace` (`../net-trace/SKILL.md`), `fail-safely` (`../fail-safely/SKILL.md`), `least-privilege` (`../least-privilege/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `safe-iac` (`../safe-iac/SKILL.md`), `observable-by-default` (`../observable-by-default/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.

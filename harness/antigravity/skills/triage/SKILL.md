---
name: triage
description: "Isolate live infrastructure incidents across cloud, edge, cluster, and host layers without losing evidence. Use for live outages or production triage."
disable-model-invocation: true
---

# Triage

Isolate live infrastructure and distributed-systems failures without destroying evidence or worsening the outage. Stabilize safely first, prove root cause, and hand permanent fixes downstream.

Hand confirmed code or IaC bugs to **bugbash** once isolated. Discover active provider CLIs, APIs, and telemetry via **analyze-environment**—never assume a fixed vendor list.

## 1. Lock context and preserve volatile evidence first

1. **Verify target environment (`analyze-environment`, `jack-in`):** confirm exact account, project, region, cluster/namespace, and IaC workspace in `TOOLS.md` first. Never mutate production without explicit approval (**decisions-in-plain-words**).
2. **Capture volatile state first:** grab crash evidence before any restart or drain, because restarts erase it. Collect current and previous logs, platform events, thread dumps, open FDs/sockets, conntrack/DNS/metrics snapshots, and error traces. Persist scrubbed logs, traces, and metrics under `$HOME/.astack/<project_name>/logging/<logs|traces|metrics>/[FILE_YYYY_MM_DD_HH_MM_SS]` (`%USERPROFILE%\.astack\...` on Windows; `astack-tools logging path`) with zero secrets (**no-leaked-secrets**). Keep temporary local scratch captures named `<file>_DEBUG_<shorthash>.<type>` and remove them afterward (**cleanup**).
3. **Pin down symptom and blast radius:** record what fails, which tenants, regions, PoPs, or services are hit, exact UTC onset, and error rate or latency.

## 2. Correlate recent changes before deep-diving

Inspect recent changes near onset with safe read-only probes:

- app, container, serverless, or edge deploys, GitOps syncs, and feature-flag flips;
- IaC applies, IAM/security merges, DNS/CDN/WAF/routing edits, and secret or TLS rotations;
- platform audit logs, autoscaling events, and upstream provider status or quota changes.

## 3. Isolate systematically across layers (read-only probes)

Lead may dispatch parallel read-only `astack-researcher` or `astack-reviewer` probes across suspect layers under `lead` clocks; Workers and Researchers probe sequentially:

- **Edge, CDN, WAF, DNS, TLS, & network (`net-trace`):** WAF/bot/rate-limit/SSL mode, LB health, DNS/DNSSEC, cert chain/SNI/mTLS, firewall rules, flow logs, packet captures, NAT/conntrack limits.
- **Compute & orchestrator:** OOMs, evictions, cold starts, CPU/disk/inode/IOPS limits, CNI networking, stuck sync hooks.
- **Process & runtime:** thread, goroutine, or pool exhaustion, FD limits, GC pauses, deadlocks, and retry storms (`fail-safely`).
- **Data, identity, & control planes:** DB locks, slow queries, WAL/vacuum bloat, queue/DLQ lag, cache stampedes, IAM/RBAC denials (`least-privilege`), quota cliffs.

Cite the exact command and observed output for every claim (`ran` vs. `read`). Never guess the failing layer.

## 4. Separate safe mitigation from permanent fix

1. **Propose reversible mitigation first (`decisions-in-plain-words`):** if service is degraded, recommend the safest reversible step (rollback, traffic drain, failover, WAF bypass, scale up, or flag off). Include blast radius, health check, and rollback path while honoring `autonomy`.
2. **Hand off root causes cleanly:**
   - Code, migration, or IaC defect -> **bugbash** with the triage dossier (`safe-to-deploy`, `safe-iac`).
   - Missing telemetry or runbook gap -> `observable-by-default` and `technical-writing`.
   - Record the timeline, disproved hypotheses (`decided:`), and guards via **lookback** + `make-it-stick`. Remove scratch/superseded captures (`cleanup`), retaining only sanitized evidence files handed off to `bugbash` or cited below (delete those once the follow-up fix lands).

## Triage Dossier (Reply)

- **Impact & timeline:** affected scope, exact UTC onset, and current status.
- **Preserved evidence:** exact retained (non-deleted) `<file>_DEBUG_<shorthash>.*` paths handed off for follow-up, plus key command outputs.
- **Isolated layer & root cause:** proven failing layer vs. ruled-out layers with `ran` evidence.
- **Mitigation & handoff:** safest reversible step (if degraded) and permanent fix handoff (`bugbash` or runbook/telemetry owner).

Referenced skills: `bugbash` (`../bugbash/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`), `lookback` (`../lookback/SKILL.md`). Read any cited skill file before acting when its trigger applies.

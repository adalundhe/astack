---
name: triage
description: "Structured live-infrastructure and multi-layer systems debugging across any cloud, edge/CDN, orchestrator, serverless, or host platform: confirm target context, preserve volatile evidence before restarts, correlate recent deploys/IaC/audit logs, isolate across layers with safe read-only probes, separate reversible mitigation from root cause, and hand confirmed code/IaC bugs to bugbash. Use for live incidents, degraded services, platform/network/auth/DB failures, or production outages."
disable-model-invocation: true
---

# Triage

Isolate live infrastructure and distributed-systems failures across cloud, edge, cluster, and host layers without destroying evidence or making the outage worse—stabilize safely first, then prove root cause and hand off permanent fixes.

Use **triage** for live environment, cloud, edge/CDN/WAF, cluster, network, identity, DB, or platform failures; hand confirmed code or IaC bugs to **bugbash** once isolated. Discover whichever provider CLIs, APIs, and observability systems apply via **analyze-environment**—never assume a fixed vendor list.

## 1. Lock context and preserve volatile evidence first

1. **Verify target environment (**analyze-environment**):** confirm exact cloud/edge account, project/subscription/zone, region, cluster/namespace, and IaC workspace/stack in `TOOLS.md` before running any command. Never run mutating commands against production without explicit human approval (**decisions-in-plain-words**).
2. **Capture volatile state *before* restarting or draining anything:** grab failing logs (including previous/crashed instance logs), orchestrator/platform events, live stack/thread/goroutine dumps, open FDs/sockets, connection-tracking/DNS/metrics snapshots, and error traces. Save artifacts as `<file>_DEBUG_<shorthash>.<type>` with zero secrets (**no-leaked-secrets**).
3. **Define the exact symptom and blast radius:** what is failing, for which tenants/regions/edge PoPs/zones/services, since what exact UTC timestamp, and at what error rate/latency?

## 2. Correlate recent changes before deep-diving

Inspect every change near the onset timestamp using safe read-only probes against the system's actual deployment and audit planes:
- application, container, serverless, or edge deploys, GitOps sync history, and feature-flag flips;
- IaC applies, identity/security-repo merges, DNS/CDN/WAF/routing edits, and secret or TLS certificate rotations;
- cloud/edge/platform audit logs, autoscaling events, and upstream provider status or quota changes.

## 3. Isolate systematically across layers (read-only probes)

Dispatch read-only `astack:researcher` / `astack:reviewer` probes in parallel across suspect layers (under **lead**'s watch/swap clocks) to bisect where the request or job breaks:

- **Edge, CDN, WAF, DNS, TLS, & L3–L7 network (**net-trace**):** edge/WAF/bot/rate-limit/Zero-Trust responses and SSL mode, load-balancer/ingress target health, DNS/DNSSEC, certificate chain/expiry/SNI/mTLS, stateful/stateless firewalls and cluster network policies, routing, flow logs, packet captures, NAT/conntrack exhaustion.
- **Compute & orchestrator (containers, serverless, edge workers, VMs, hosts):** crashes/OOMs/evictions/cold starts/compute or subrequest limits, scheduling/quotas, CPU throttling, disk/inode/IOPS saturation, host networking/CNI, stuck deploy/sync hooks.
- **Process & runtime:** thread/goroutine/connection-pool exhaustion, FD limits, GC pauses, deadlocks, retry storms (**fail-safely**).
- **Data, identity, & control planes:** DB connections, locks/blocked queries, long transactions, WAL/disk/vacuum bloat, queue lag/DLQ depth, cache stampedes, IAM/federation/RBAC/token denials (**least-privilege**), provider API throttling/quota cliffs.

Every claim must cite the exact command and observed output (ran vs. read)—never guess the failing layer.

## 4. Separate safe mitigation from permanent fix

1. **Propose reversible mitigation first (**decisions-in-plain-words**):** if service is actively degraded, present the safest reversible action (release/revision/config rollback, traffic drain or origin failover, WAF rule bypass, scale up, flag off, cert/cred fix) with its blast radius, verification check, and rollback path—respecting `autonomy.allow`/`autonomy.deny`.
2. **Hand off confirmed root causes cleanly:**
   - Code, migration, or IaC defect -> run **bugbash** with the collected triage dossier (and enforce **safe-to-deploy**, **safe-iac**, **least-privilege**, **fail-safely**).
   - Missing telemetry or runbook gap -> address via **observable-by-default** and **technical-writing**.
   - Record the incident timeline, disproved hypotheses (`decided:`), and structural preventions via **make-it-stick**, then remove temporary debug captures (**cleanup**).

Referenced skills: `bugbash` (`${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`), `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `net-trace` (`${CLAUDE_SKILL_DIR}/../net-trace/SKILL.md`), `fail-safely` (`${CLAUDE_SKILL_DIR}/../fail-safely/SKILL.md`), `least-privilege` (`${CLAUDE_SKILL_DIR}/../least-privilege/SKILL.md`), `safe-to-deploy` (`${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md`), `safe-iac` (`${CLAUDE_SKILL_DIR}/../safe-iac/SKILL.md`), `observable-by-default` (`${CLAUDE_SKILL_DIR}/../observable-by-default/SKILL.md`), `technical-writing` (`${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.

---
name: safe-to-deploy
description: "Keep live workloads and rollbacks safe across every deploy step using expand-switch-contract. Use for DB migrations, auth/identity, cloud/edge/DNS/WAF infra, or contract changes."
---

# Safe to deploy

Keep live workloads running through every migration, auth, infra/DNS/edge, or contract rollout. Every step must survive a rollback unless the person approved downtime.

Apply this across whatever runtime, orchestrator, serverless, edge, database, or cloud platform the system uses (`analyze-environment`).

## Start with

1. **Map the live transition window (`blast-radius`):** list every live consumer across repos, not just the end state. Include rolling compute, cron/queued jobs, migration hooks, DNS/CDN/TLS cutovers, infra stacks, and the rolled-back release.
2. **Ship breaking cutovers as expand -> switch -> contract:**
   - **Expand:** add the new identity, grant, schema, endpoint, route, or cert while keeping existing callers working. Lower DNS TTLs and validate certs before flipping traffic.
   - **Switch & verify:** roll services, scheduled jobs, and cross-repo callers progressively (canary/small slice first when supported). Verify post-deploy health, SLOs, error rates, and zero remaining traffic on the old path (`observable-by-default`, `prove-it`) before promoting to 100% or contracting; roll back via `unland` on regression.
   - **Contract:** revoke old privileges or drop old columns/routes in a **later release**. Wait until rollback is no longer needed because early cleanup breaks prior releases.
3. **Keep rollback working at every commit**. If a service rolls back *after* a DB or infra change commits, pre-change workloads must still function.
4. **Test mixed versions (**prove-it**, `full-spectrum-testing`):** run pre-change code and real non-privileged roles against post-migration state, plus rollback. Never test only new code on new state, because that hides live transition breakage.
5. **Escalate unavoidable outages upfront (`decisions-in-plain-words`, `technical-writing`):** get human sign-off first. Document impact, deploy order, and rollback steps in both PR and runbook.

## Watch for

- migrations or hooks revoking privileges, dropping/renaming columns, or tightening constraints before old workloads roll off;
- revoking role membership or ownership without preserving grants for running legacy identities;
- DNS/CDN/WAF or TLS flips made before new origin certs validate or high TTLs drain;
- cross-repo or infra changes applied out of order ahead of app rollout;
- changes that brick rollback to the prior release;
- tests using admin credentials or only the new identity while skipping pre-change queries;
- PR bodies or runbooks silent about deploy ordering, downtime, or cleanup.

**The test:** after this change commits, can every pre-PR workload, job, and rolled-back release still operate cleanly?

## When it doesn't fit

- greenfield systems with no live workloads or persisted data;
- a planned maintenance window explicitly approved by the person and documented in the PR and runbook.

**Showing it:** apply the change against a pre-PR environment. Run real queries as the pre-PR non-privileged identity and from a rolled-back version to expose the failure.

Referenced skills: `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

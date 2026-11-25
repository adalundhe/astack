---
name: safe-to-deploy
description: "Keep live workloads and rollbacks working across every deploy step using expand-switch-contract, mixed-version testing, and cross-repo deploy ordering. Use for DB migrations, auth/identity, cloud/edge/DNS/WAF infra, deploy waves, or contract changes."
disable-model-invocation: true
---

# Safe to deploy

Every migration, auth change, infra/DNS/edge update, or contract change must keep live workloads running throughout the rollout and survive a rollback, unless the person explicitly approved downtime.

Apply this across whatever runtime, orchestrator, serverless, edge, database, or cloud platform the system uses (**analyze-environment**).

## Start with

1. **Map the live transition window, not just the end state (**blast-radius**):** list every live consumer across repos—rolling compute, scheduled and queued jobs, pre-deploy migration hooks, DNS/CDN/WAF/TLS cutovers, infra stacks, and the prior release if rolled back.
2. **Ship breaking cutovers as expand -> switch -> contract:**
   - **Expand:** add the new identity, grant, schema, endpoint, route, or cert while keeping least-privilege access working for existing live callers. Lower DNS TTLs and validate certs before flipping traffic.
   - **Switch & verify:** roll services, scheduled jobs, and cross-repo callers onto the new path and verify zero live traffic remains on the old path.
   - **Contract:** revoke old privileges or drop old columns/routes in a **later release** once rollback to the prior release is no longer needed.
3. **Keep rollback working at every commit:** if a service or chart rolls back *after* a DB migration or infra change commits, pre-change workloads must still connect and function.
4. **Test mixed versions with real non-privileged identities (**prove-it**, **full-spectrum-testing**):** run pre-change code and real non-privileged roles against post-migration state, and test rollback. Never test only new code against new state.
5. **Escalate unavoidable outages upfront (**decisions-in-plain-words**, **technical-writing**):** get human sign-off first and document impact, deploy order, and rollback steps in both PR and runbook.

## Watch for

- migrations or hooks that revoke privileges, drop/rename columns, or tighten constraints before old workloads and cron jobs roll off;
- revoking role membership or ownership without preserving grants for still-running legacy identities;
- DNS/CDN/WAF or TLS flips made before new origin certs validate or high TTLs drain;
- cross-repo or infra changes applied out of order ahead of app rollout;
- changes that brick rollback to the prior release;
- tests using admin credentials or only the new identity while skipping pre-change queries;
- PR bodies or runbooks silent about deploy ordering, downtime, or cleanup.

**The test:** after this change commits, can every pre-PR workload, scheduled job, queued task, and rolled-back release still operate cleanly?

## When it doesn't fit

- greenfield systems with no live workloads or persisted data;
- a planned maintenance window explicitly approved by the person and documented in the PR and runbook.

**Showing it:** apply the change against a pre-PR environment and run real queries as the pre-PR non-privileged identity (and from a rolled-back version) to expose the exact failure.

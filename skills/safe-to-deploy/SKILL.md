---
name: safe-to-deploy
description: "Keep live workloads and rollbacks working across every deploy step using expand-switch-contract, mixed-version testing, and cross-repo deploy ordering. Use when writing or reviewing DB migrations, auth/identity changes, cloud/edge/DNS/WAF infra, deploy waves, APIs, or schema/wire changes."
disable-model-invocation: true
---

# Safe to deploy

Every migration, auth/identity change, infra/DNS/edge update, or contract change must keep live workloads running throughout the deploy window and survive a rollback—unless the person explicitly approved downtime.

Apply these principles across whatever runtime, orchestrator, serverless, edge, database, or cloud platform the system runs on (**analyze-environment**).

## Start with

1. **Map the live transition window, not just the end state (**blast-radius**):** list every live consumer and deploy hook across repos and platforms—rolling compute (containers, VMs, serverless/edge revisions), scheduled and queued jobs, pre-deploy/sync-wave migration hooks, DNS/CDN/WAF/TLS cutovers (lower TTLs and validate certificates before flipping traffic), security/infra stacks, and the prior release if rolled back.
2. **Ship breaking cutovers as expand -> switch -> contract:**
   - **Expand:** add the new identity, grant, schema, endpoint, route, or certificate while preserving least-privilege access for existing live callers (e.g., retain explicit table/sequence grants for a retiring DB user during ownership handover, or keep dual origins/certs valid before flipping DNS).
   - **Switch & verify:** roll all services, edge/serverless workloads, scheduled jobs, and cross-repo callers onto the new path and verify zero live traffic remains on the old path.
   - **Contract:** revoke old privileges/identities or drop old columns/routes in a **later release** (or explicit post-cutover retirement step) once rollback to the prior release is no longer needed.
3. **Keep rollback working at every commit:** if any service, revision, config, or chart rolls back *after* a DB migration or infra change commits, pre-change workloads must still connect, query, and function.
4. **Test mixed versions with real non-privileged identities (**prove-it**, **full-spectrum-testing**):** run pre-change code and real non-privileged roles/tokens against post-migration state, and verify rollback—never test only new code against new state.
5. **Escalate unavoidable outages explicitly (**decisions-in-plain-words**, **technical-writing**):** if downtime is genuinely unavoidable, get the person's sign-off up front and state the impact, ordering, and rollback steps plainly in both the PR body and runbook.

## Watch for

- migrations or pre-deploy hooks that revoke privileges, drop/rename columns, or tighten constraints before old workloads and scheduled/queued jobs have rolled off;
- revoking role membership or ownership without preserving explicit grants for still-running legacy identities;
- DNS/CDN/WAF or TLS changes flipped before new origin certificates validate or high TTLs drain;
- cross-repo or infra/security changes whose deploy order breaks callers if applied ahead of application rollout;
- migrations or config changes that brick rollback to the prior release;
- tests using admin/superuser credentials or only the new identity while skipping pre-change caller queries;
- PR bodies or retirement runbooks silent about deploy ordering, downtime, or cleanup steps.

**The test:** after this migration/infra/edge step commits, can every pre-PR workload, scheduled job, queued task, and a rolled-back release still operate cleanly?

## When it doesn't fit

- greenfield systems with no live workloads or persisted data yet;
- a planned maintenance window explicitly approved by the person and documented in the PR and runbook.

**Showing it:** apply the migration/infra change against a pre-PR environment and execute real queries/requests as the pre-PR non-privileged identity (and from a rolled-back version); show the permission, schema, DNS/TLS, or contract failure.
